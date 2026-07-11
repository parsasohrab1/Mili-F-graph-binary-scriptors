"""High-level BNN descriptor extraction API (FR-1)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import yaml
from numpy.typing import NDArray

from mili_vio.descriptors.bnn.driver import BNNDriver, EnergyModel, SPIDMADriver, SimulatedBNNDriver, SPIConfig
from mili_vio.descriptors.bnn.protocol import BNNStatus
from mili_vio.types import BinaryDescriptor


@dataclass
class ExtractionResult:
    descriptors: list[BinaryDescriptor]
    keypoints_uv: list[NDArray[np.float64]]
    responses: list[float]
    extraction_time_ms: float
    energy_mj: float
    source: str  # "bnn" | "fallback"
    num_keypoints: int


@dataclass
class ExtractionMetrics:
    mean_time_ms: float
    max_time_ms: float
    mean_repeatability: float
    mean_energy_mj: float
    meets_time_spec: bool
    meets_repeatability_spec: bool
    meets_energy_spec: bool


def load_phase3_config(path: Optional[Path] = None) -> dict:
    if path is None:
        path = Path(__file__).resolve().parents[4] / "configs" / "phase3.yaml"
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class BNNDescriptorAPI:
    """
    FR-1 API: 128-bit binary descriptor extraction via BNN chip.

    Supports SPI/DMA driver and automatic fallback to ORB/BRIEF.
    """

    def __init__(
        self,
        config: Optional[dict] = None,
        driver: Optional[BNNDriver] = None,
    ) -> None:
        self._cfg = config or load_phase3_config()
        p3 = self._cfg.get("phase3", {})
        bnn_cfg = p3.get("bnn", {})
        energy_cfg = p3.get("energy_model", {})

        self.max_keypoints = bnn_cfg.get("max_keypoints", 200)
        self.descriptor_bits = bnn_cfg.get("descriptor_bits", 128)
        self.energy_model = EnergyModel(
            base_mj=energy_cfg.get("base_mj", 0.5),
            per_keypoint_mj=energy_cfg.get("per_keypoint_mj", 0.02),
            per_bit_mj=energy_cfg.get("per_bit_mj", 0.001),
        )
        self.acceptance = p3.get("acceptance", {})

        if driver is not None:
            self._driver = driver
        elif bnn_cfg.get("transport") == "simulated" or bnn_cfg.get("enabled", True):
            spi = bnn_cfg.get("spi", {})
            self._driver = SPIDMADriver(
                SPIConfig(
                    bus_id=spi.get("bus_id", 0),
                    cs_pin=spi.get("cs_pin", 10),
                    clock_hz=spi.get("clock_hz", 20_000_000),
                    dma_channel=spi.get("dma_channel", 1),
                ),
                backend=SimulatedBNNDriver(self.energy_model),
            )
        else:
            self._driver = SimulatedBNNDriver(self.energy_model)

        self._fallback = None
        if p3.get("fallback", {}).get("enabled", True):
            from mili_vio.descriptors.fallback import SoftwareFallbackExtractor
            fb_type = p3.get("fallback", {}).get("descriptor_type", "orb")
            self._fallback = SoftwareFallbackExtractor(fb_type, self.max_keypoints)

    def extract(
        self,
        image: NDArray[np.uint8],
        max_keypoints: Optional[int] = None,
        force_fallback: bool = False,
    ) -> ExtractionResult:
        limit = min(max_keypoints or self.max_keypoints, self.max_keypoints)
        start = time.perf_counter()

        if force_fallback and self._fallback:
            return self._extract_fallback(image, limit, start)

        response = self._driver.extract(image, limit)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if response.status != BNNStatus.OK and self._fallback:
            return self._extract_fallback(image, limit, start)

        descriptors: list[BinaryDescriptor] = []
        keypoints_uv: list[NDArray[np.float64]] = []
        responses: list[float] = []

        for i, kp in enumerate(response.keypoints):
            descriptors.append(BinaryDescriptor(bits=kp.descriptor_bits.copy(), keypoint_id=i))
            keypoints_uv.append(np.array([kp.x, kp.y], dtype=np.float64))
            responses.append(kp.response)

        energy_mj = response.energy_uj / 1000.0 if response.energy_uj else self.energy_model.estimate(len(descriptors))

        return ExtractionResult(
            descriptors=descriptors,
            keypoints_uv=keypoints_uv,
            responses=responses,
            extraction_time_ms=elapsed_ms,
            energy_mj=energy_mj,
            source="bnn",
            num_keypoints=len(descriptors),
        )

    def _extract_fallback(
        self,
        image: NDArray[np.uint8],
        limit: int,
        start: float,
    ) -> ExtractionResult:
        assert self._fallback is not None
        result = self._fallback.extract(image, limit)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return ExtractionResult(
            descriptors=result.descriptors,
            keypoints_uv=result.keypoints_uv,
            responses=result.responses,
            extraction_time_ms=elapsed_ms,
            energy_mj=self.energy_model.estimate(len(result.descriptors)) * 2.5,
            source="fallback",
            num_keypoints=len(result.descriptors),
        )

    def measure_repeatability(
        self,
        image_a: NDArray[np.uint8],
        image_b: NDArray[np.uint8],
    ) -> float:
        from mili_vio.descriptors.matching import BinaryMatcher

        ext_a = self.extract(image_a)
        ext_b = self.extract(image_b)
        if not ext_a.descriptors or not ext_b.descriptors:
            return 0.0

        matcher = BinaryMatcher()
        matches = matcher.match(ext_a.descriptors, ext_b.descriptors)
        return len(matches) / min(len(ext_a.descriptors), len(ext_b.descriptors))

    def benchmark_sequence(
        self,
        images: list[NDArray[np.uint8]],
    ) -> ExtractionMetrics:
        times: list[float] = []
        energies: list[float] = []
        repeatabilities: list[float] = []

        for i, img in enumerate(images):
            result = self.extract(img)
            times.append(result.extraction_time_ms)
            energies.append(result.energy_mj)
            if i > 0:
                rep = self.measure_repeatability(images[i - 1], img)
                repeatabilities.append(rep)

        acc = self.acceptance
        mean_rep = float(np.mean(repeatabilities)) if repeatabilities else 0.0
        mean_time = float(np.mean(times)) if times else 0.0
        max_time = float(np.max(times)) if times else 0.0
        mean_energy = float(np.mean(energies)) if energies else 0.0

        return ExtractionMetrics(
            mean_time_ms=mean_time,
            max_time_ms=max_time,
            mean_repeatability=mean_rep,
            mean_energy_mj=mean_energy,
            meets_time_spec=max_time < acc.get("extraction_time_ms", 2.0),
            meets_repeatability_spec=mean_rep * 100 >= acc.get("repeatability_pct", 90.0),
            meets_energy_spec=mean_energy < acc.get("energy_mj_per_frame", 5.0),
        )
