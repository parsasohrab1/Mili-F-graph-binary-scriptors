"""SRS hardware validation for FR-1 BNN descriptor extraction."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import yaml
from numpy.typing import NDArray

from mili_vio.descriptors.bnn.api import BNNDescriptorAPI, load_phase3_config
from mili_vio.descriptors.bnn.driver import create_bnn_driver
from mili_vio.descriptors.bnn.protocol import BNNStatus


@dataclass
class SRSExtractionReport:
    transport: str
    is_hardware: bool
    frames_tested: int
    mean_chip_time_ms: float
    max_chip_time_ms: float
    mean_wall_time_ms: float
    mean_repeatability_pct: float
    mean_energy_mj: float
    max_energy_mj: float
    meets_time_spec: bool
    meets_repeatability_spec: bool
    meets_energy_spec: bool
    hardware_connected: bool
    all_pass: bool
    notes: list[str]


def perturb_image(image: NDArray[np.uint8], flip_prob: float = 0.15) -> NDArray[np.uint8]:
    """Slightly perturb image to test descriptor repeatability (SRS > 90%)."""
    out = image.copy()
    mask = np.random.random(out.shape) < flip_prob
    out[mask] = 255 - out[mask]
    return out


def generate_validation_sequence(
    num_frames: int = 20,
    width: int = 640,
    height: int = 480,
    seed: int = 42,
) -> list[NDArray[np.uint8]]:
    rng = np.random.default_rng(seed)
    images: list[NDArray[np.uint8]] = []
    base = np.zeros((height, width), dtype=np.uint8)
    for i in range(8):
        x0 = int(rng.integers(40, width - 120))
        y0 = int(rng.integers(40, height - 120))
        cv2.rectangle(base, (x0, y0), (x0 + 80, y0 + 60), int(rng.integers(80, 220)), -1)

    for i in range(num_frames):
        if i % 2 == 0:
            images.append(base.copy())
        else:
            images.append(perturb_image(base, flip_prob=0.12 + 0.03 * (i % 3)))
    return images


def validate_bnn_srs(
    config: Optional[dict] = None,
    num_frames: int = 20,
    transport: Optional[str] = None,
    serial_port: str = "",
) -> SRSExtractionReport:
    """
    Run FR-1 SRS acceptance validation against BNN Product 1.

    Metrics:
      - extraction time: chip-reported extraction_time_us (< 2 ms)
      - repeatability: descriptor match on perturbed pairs (> 90%)
      - energy: chip-reported energy_uj (< 5 mJ/frame)
    """
    cfg = config or load_phase3_config()
    p3 = cfg.get("phase3", {})
    bnn_cfg = p3.get("bnn", {})
    acc = p3.get("acceptance", {})
    notes: list[str] = []

    if transport:
        bnn_cfg = {**bnn_cfg, "transport": transport}
        cfg = {**cfg, "phase3": {**p3, "bnn": bnn_cfg}}

    if serial_port:
        bnn_cfg = {**bnn_cfg, "serial_port": serial_port}
        cfg = {**cfg, "phase3": {**p3, "bnn": bnn_cfg}}

    driver = create_bnn_driver(cfg)
    api = BNNDescriptorAPI(config=cfg, driver=driver)
    is_hw = getattr(driver, "is_hardware", False)

    images = generate_validation_sequence(num_frames)
    chip_times_ms: list[float] = []
    wall_times_ms: list[float] = []
    energies_mj: list[float] = []
    repeatabilities: list[float] = []

    for i, img in enumerate(images):
        response = driver.extract(img, api.max_keypoints)
        if response.status != BNNStatus.OK:
            notes.append(f"frame {i}: BNN status {response.status.name}")
            continue

        chip_ms = response.extraction_time_us / 1000.0
        if response.extraction_time_us > 0:
            chip_times_ms.append(chip_ms)
        energy_mj = response.energy_uj / 1000.0 if response.energy_uj else 0.0
        energies_mj.append(energy_mj)

        result = api.extract(img)
        wall_times_ms.append(result.extraction_time_ms)

        if i > 0:
            rep = api.measure_repeatability(images[i - 1], img) * 100.0
            repeatabilities.append(rep)

    hw_connected = is_hw and len(chip_times_ms) > 0
    if not is_hw:
        notes.append("Using loopback/simulated transport — connect spidev or serial for Product 1")
    elif not hw_connected:
        notes.append("Hardware transport configured but no valid chip responses")

    time_limit = acc.get("extraction_time_ms", 2.0)
    rep_limit = acc.get("repeatability_pct", 90.0)
    energy_limit = acc.get("energy_mj_per_frame", 5.0)

    max_chip = max(chip_times_ms) if chip_times_ms else 999.0
    mean_chip = float(np.mean(chip_times_ms)) if chip_times_ms else 999.0
    mean_wall = float(np.mean(wall_times_ms)) if wall_times_ms else 0.0
    mean_rep = float(np.mean(repeatabilities)) if repeatabilities else 0.0
    mean_energy = float(np.mean(energies_mj)) if energies_mj else 999.0
    max_energy = max(energies_mj) if energies_mj else 999.0

    meets_time = max_chip < time_limit
    meets_rep = mean_rep >= rep_limit
    meets_energy = max_energy < energy_limit

    return SRSExtractionReport(
        transport=bnn_cfg.get("transport", "simulated"),
        is_hardware=is_hw,
        frames_tested=len(images),
        mean_chip_time_ms=mean_chip,
        max_chip_time_ms=max_chip,
        mean_wall_time_ms=mean_wall,
        mean_repeatability_pct=mean_rep,
        mean_energy_mj=mean_energy,
        max_energy_mj=max_energy,
        meets_time_spec=meets_time,
        meets_repeatability_spec=meets_rep,
        meets_energy_spec=meets_energy,
        hardware_connected=hw_connected,
        all_pass=meets_time and meets_rep and meets_energy,
        notes=notes,
    )


def save_srs_report(report: SRSExtractionReport, output_dir: Path | str) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "fr1_srs_validation.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(asdict(report), f, default_flow_style=False)
    return path
