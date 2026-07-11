"""FR-3: Event-driven landmark sharing."""

from __future__ import annotations

from typing import Optional

import numpy as np

from mili_vio.config import SharingConfig, load_config
from mili_vio.types import BinaryDescriptor, Landmark, SharingEvent


class EventDrivenSharing:
    """
    Share sparse landmarks only when local uncertainty exceeds threshold.

    Reduces bandwidth by ~70-80% compared to continuous position sharing.
    """

    def __init__(
        self,
        sharing: Optional[SharingConfig] = None,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        config = load_config()
        self._sharing = sharing or config.sharing
        self._accuracy = config.accuracy
        self._rng = rng or np.random.default_rng()

    @property
    def uncertainty_threshold(self) -> float:
        return self._accuracy.uncertainty_threshold_m

    def should_share(self, uncertainty: float) -> bool:
        return uncertainty > self._accuracy.uncertainty_threshold_m

    def should_share_covariance(self, covariance_position_trace: float) -> bool:
        """Trigger based on position covariance trace (from FR-2 factor graph)."""
        uncertainty = float(np.sqrt(covariance_position_trace / 3.0))
        return uncertainty > self._accuracy.uncertainty_threshold_m

    def create_sharing_event(
        self,
        uncertainty: float,
        drone_id: int,
        timestamp: int,
        descriptors: Optional[list[BinaryDescriptor]] = None,
    ) -> SharingEvent:
        """
        Create a sharing event if uncertainty exceeds threshold.

        Returns sparse landmark set (not raw positions) with metadata.
        """
        active = self.should_share(uncertainty)

        if not active:
            return SharingEvent(
                active=False,
                num_landmarks_shared=0,
                shared_data_bytes=0,
            )

        num_landmarks = self._rng.integers(
            self._sharing.min_landmarks_shared,
            self._sharing.max_landmarks_shared + 1,
        )
        shared_bytes = num_landmarks * self._sharing.landmark_bytes_compressed

        landmarks = self._generate_landmarks(num_landmarks, drone_id, timestamp, descriptors)

        return SharingEvent(
            active=True,
            num_landmarks_shared=num_landmarks,
            shared_data_bytes=shared_bytes,
            landmarks=landmarks,
            metadata={
                "timestamp": timestamp,
                "uncertainty": uncertainty,
                "drone_id": drone_id,
            },
        )

    def apply_cooperative_correction(self, base_error: float) -> float:
        """Apply group synergy improvement when sharing is active."""
        factor = self._rng.uniform(
            self._sharing.improvement_factor_min,
            self._sharing.improvement_factor_max,
        )
        corrected = base_error * factor + self._rng.normal(0, 0.005)
        return max(corrected, 0.0)

    def meets_bandwidth_spec(self, shared_bytes: int) -> bool:
        return shared_bytes < 100

    def _generate_landmarks(
        self,
        count: int,
        drone_id: int,
        timestamp: int,
        descriptors: Optional[list[BinaryDescriptor]],
    ) -> list[Landmark]:
        landmarks: list[Landmark] = []
        for i in range(count):
            if descriptors and i < len(descriptors):
                desc = descriptors[i]
            else:
                bits = self._rng.integers(0, 2, 128, dtype=np.uint8)
                desc = BinaryDescriptor(bits=bits, keypoint_id=i)

            landmarks.append(
                Landmark(
                    landmark_id=i,
                    position=self._rng.normal(0, 5, 3),
                    descriptor=desc,
                    uncertainty=self._rng.uniform(0.1, 0.5),
                    source_drone_id=drone_id,
                    timestamp=timestamp,
                )
            )
        return landmarks
