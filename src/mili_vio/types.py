"""Shared data types for the cooperative VIO system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np
from numpy.typing import NDArray


class ScenarioType(str, Enum):
    URBAN_CANYON = "urban_canyon"
    FOREST_DENSE = "forest_dense"
    INDOOR_COMPLEX = "indoor_complex"
    OPEN_FIELD = "open_field"


class CommunicationQuality(str, Enum):
    CLEAR = "clear"
    INTERMITTENT = "intermittent"
    JAMMED = "jammed"


@dataclass(frozen=True)
class IMUReading:
    accel: NDArray[np.float64]  # shape (3,)
    gyro: NDArray[np.float64]  # shape (3,)
    timestamp: int


@dataclass(frozen=True)
class Pose6DOF:
    position: NDArray[np.float64]  # shape (3,) - x, y, z
    orientation: NDArray[np.float64]  # shape (3,) - roll, pitch, yaw


@dataclass
class BinaryDescriptor:
    bits: NDArray[np.uint8]  # shape (128,) values 0 or 1
    keypoint_id: int = 0

    @property
    def hash_summary(self) -> int:
        return int(np.sum(self.bits) % 256)

    def hamming_distance(self, other: BinaryDescriptor) -> int:
        return int(np.sum(self.bits != other.bits))


@dataclass
class Landmark:
    landmark_id: int
    position: NDArray[np.float64]  # shape (3,)
    descriptor: BinaryDescriptor
    uncertainty: float
    source_drone_id: int
    timestamp: int


@dataclass
class StateEstimate:
    pose: Pose6DOF
    uncertainty: float
    localization_error_m: float
    method_type: str = "factor_graph_binary_descriptor"


@dataclass
class SharingEvent:
    active: bool
    num_landmarks_shared: int
    shared_data_bytes: int
    landmarks: list[Landmark] = field(default_factory=list)
    metadata: Optional[dict] = None
