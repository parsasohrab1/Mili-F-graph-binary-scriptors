"""Graph node definitions for FR-2 factor graph."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray


@dataclass
class PoseNode:
    index: int
    timestamp_ns: int
    position: NDArray[np.float64]
    rotation: NDArray[np.float64]
    fixed: bool = False


@dataclass
class LandmarkNode:
    index: int
    landmark_id: int
    position: NDArray[np.float64]
    observations: list[tuple[int, NDArray[np.float64]]] = field(default_factory=list)


@dataclass
class VisualObservation:
    pose_index: int
    landmark_id: int
    uv: NDArray[np.float64]
    descriptor_id: int = 0
