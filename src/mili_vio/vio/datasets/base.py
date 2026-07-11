"""VIO dataset types and base loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator, Optional

import numpy as np
from numpy.typing import NDArray


class DatasetType(str, Enum):
    EUROC = "euroc"
    TUM_VI = "tum_vi"
    SYNTHETIC = "synthetic"


@dataclass(frozen=True)
class CameraFrame:
    timestamp_ns: int
    image: NDArray[np.uint8]
    frame_id: int


@dataclass(frozen=True)
class IMUSample:
    timestamp_ns: int
    gyro: NDArray[np.float64]
    accel: NDArray[np.float64]


@dataclass(frozen=True)
class GroundTruthPose:
    timestamp_ns: int
    position: NDArray[np.float64]
    quaternion: NDArray[np.float64]  # [qw, qx, qy, qz]


@dataclass
class CameraIntrinsics:
    fx: float
    fy: float
    cx: float
    cy: float
    width: int = 752
    height: int = 480


@dataclass
class VIODataset:
    name: str
    dataset_type: DatasetType
    intrinsics: CameraIntrinsics
    frames: list[CameraFrame] = field(default_factory=list)
    imu: list[IMUSample] = field(default_factory=list)
    ground_truth: list[GroundTruthPose] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.frames)

    def iter_frames(self, max_frames: Optional[int] = None) -> Iterator[CameraFrame]:
        limit = max_frames or len(self.frames)
        for frame in self.frames[:limit]:
            yield frame

    def imu_between(self, t_start: int, t_end: int) -> list[IMUSample]:
        return [s for s in self.imu if t_start <= s.timestamp_ns <= t_end]

    def ground_truth_at(self, timestamp_ns: int) -> Optional[GroundTruthPose]:
        if not self.ground_truth:
            return None
        times = np.array([g.timestamp_ns for g in self.ground_truth])
        idx = int(np.argmin(np.abs(times - timestamp_ns)))
        return self.ground_truth[idx]


def resolve_dataset_path(root: Path, dataset_type: DatasetType, sequence: str) -> Path:
    return root / dataset_type.value / sequence
