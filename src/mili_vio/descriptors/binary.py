"""FR-1: Binary visual descriptor extraction."""

from __future__ import annotations

from typing import Optional

import numpy as np
from numpy.typing import NDArray

from mili_vio.config import HardwareConfig, load_config
from mili_vio.descriptors.bnn.api import BNNDescriptorAPI, ExtractionResult
from mili_vio.types import BinaryDescriptor


class BinaryDescriptorExtractor:
    """
    Extract 128-bit binary descriptors from grayscale camera frames.

    Delegates to BNN hardware API with automatic ORB/BRIEF fallback.
    """

    def __init__(
        self,
        hardware: Optional[HardwareConfig] = None,
        rng: Optional[np.random.Generator] = None,
        use_bnn: bool = True,
    ) -> None:
        config = load_config() if hardware is None else None
        self._hw = hardware or (config.hardware if config else HardwareConfig())
        self._rng = rng or np.random.default_rng()
        self._api = BNNDescriptorAPI() if use_bnn else None
        self._last_result: ExtractionResult | None = None

    @property
    def num_bits(self) -> int:
        return self._hw.descriptor_bits

    @property
    def max_keypoints(self) -> int:
        return self._hw.max_keypoints

    @property
    def last_extraction_time_ms(self) -> float:
        return self._last_result.extraction_time_ms if self._last_result else 0.0

    @property
    def last_energy_mj(self) -> float:
        return self._last_result.energy_mj if self._last_result else 0.0

    def extract(
        self,
        image: NDArray[np.uint8],
        num_keypoints: Optional[int] = None,
    ) -> list[BinaryDescriptor]:
        if image.ndim != 2:
            raise ValueError("Image must be grayscale (2D array)")

        limit = min(num_keypoints or self._hw.max_keypoints, self._hw.max_keypoints)

        if self._api is not None:
            self._last_result = self._api.extract(image, limit)
            return self._last_result.descriptors

        return self._simulate_extract(limit)

    def _simulate_extract(self, count: int) -> list[BinaryDescriptor]:
        """Legacy simulation path when BNN API disabled."""
        descriptors: list[BinaryDescriptor] = []
        for kp_id in range(count):
            bits = self._rng.integers(0, 2, size=self._hw.descriptor_bits, dtype=np.uint8)
            descriptors.append(BinaryDescriptor(bits=bits, keypoint_id=kp_id))
        return descriptors

    def reset(self) -> None:
        self._last_result = None
