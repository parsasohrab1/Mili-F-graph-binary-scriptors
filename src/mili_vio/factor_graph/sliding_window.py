"""Sliding-window factor graph with memory budget management."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from mili_vio.factor_graph.factors import triangulate_landmark
from mili_vio.factor_graph.nodes import LandmarkNode, PoseNode, VisualObservation
from mili_vio.factor_graph.optimizer import (
    FastFactorGraphOptimizer,
    IMUFactorData,
    LoopFactorData,
    OptimizationReport,
    VisualFactorData,
)
from mili_vio.vio.backend.pose_utils import pose_to_vector, vector_to_pose
from mili_vio.vio.datasets.base import CameraIntrinsics
from mili_vio.vio.imu_preintegration import IMUPreintegrated


BYTES_PER_POSE = 64
BYTES_PER_LANDMARK = 40
BYTES_PER_FACTOR = 32


@dataclass
class MemoryReport:
    used_bytes: int
    budget_bytes: int
    num_poses: int
    num_landmarks: int
    num_factors: int

    @property
    def within_budget(self) -> bool:
        return self.used_bytes <= self.budget_bytes


@dataclass
class SlidingWindowState:
    poses: list[PoseNode] = field(default_factory=list)
    landmarks: list[LandmarkNode] = field(default_factory=list)
    imu_factors: list[IMUFactorData] = field(default_factory=list)
    visual_factors: list[VisualFactorData] = field(default_factory=list)
    loop_factors: list[LoopFactorData] = field(default_factory=list)
    landmark_id_counter: int = 0
    last_optimization: OptimizationReport | None = None


class SlidingWindowFactorGraph:
    """
    Sliding-window factor graph with pose + landmark nodes.

    Supports IMU, visual reprojection, and loop-closure factors.
    Enforces memory budget (SRS: <= 2MB).
    """

    def __init__(
        self,
        intrinsics: CameraIntrinsics,
        max_poses: int = 12,
        max_landmarks: int = 80,
        memory_budget_bytes: int = 2 * 1024 * 1024,
        optimizer: FastFactorGraphOptimizer | None = None,
    ) -> None:
        self.intrinsics = intrinsics
        self.max_poses = max_poses
        self.max_landmarks = max_landmarks
        self.memory_budget_bytes = memory_budget_bytes
        self.optimizer = optimizer or FastFactorGraphOptimizer()
        self.state = SlidingWindowState()

    def add_pose(
        self,
        timestamp_ns: int,
        position: NDArray[np.float64],
        rotation: NDArray[np.float64],
        fixed: bool = False,
    ) -> int:
        idx = len(self.state.poses)
        self.state.poses.append(
            PoseNode(idx, timestamp_ns, position.copy(), rotation.copy(), fixed)
        )
        self._enforce_limits()
        return len(self.state.poses) - 1

    def add_imu_factor(
        self,
        pose_i: int,
        pose_j: int,
        preint: IMUPreintegrated,
    ) -> None:
        if preint.dt <= 0:
            return
        self.state.imu_factors.append(
            IMUFactorData(pose_i, pose_j, preint.delta_p.copy(), preint.delta_R.copy())
        )

    def add_visual_observation(
        self,
        pose_i: int,
        uv: NDArray[np.float64],
        landmark_id: int | None = None,
        sqrt_info: float = 1.0,
    ) -> int:
        if landmark_id is None:
            pose_vec = pose_to_vector(
                self.state.poses[pose_i].position,
                self.state.poses[pose_i].rotation,
            )
            if pose_i > 0:
                prev = pose_to_vector(
                    self.state.poses[pose_i - 1].position,
                    self.state.poses[pose_i - 1].rotation,
                )
                pos = triangulate_landmark(prev, pose_vec, uv, uv, self.intrinsics)
            else:
                pos = self.state.poses[pose_i].position + self.state.poses[pose_i].rotation @ np.array([0, 0, 3.0])

            lm_idx = len(self.state.landmarks)
            self.state.landmarks.append(
                LandmarkNode(lm_idx, self.state.landmark_id_counter, pos)
            )
            self.state.landmark_id_counter += 1
            landmark_id = lm_idx

        self.state.visual_factors.append(
            VisualFactorData(pose_i, landmark_id, uv.copy(), sqrt_info)
        )
        self.state.landmarks[landmark_id].observations.append((pose_i, uv.copy()))
        self._enforce_limits()
        return landmark_id

    def add_shared_landmark(
        self,
        pose_i: int,
        position: NDArray[np.float64],
        landmark_id: int,
        uv: NDArray[np.float64] | None = None,
        sqrt_info: float = 2.0,
    ) -> int:
        """Integrate landmark received from another drone into factor graph."""
        if uv is None:
            uv = np.array([320.0, 240.0])

        lm_idx = len(self.state.landmarks)
        self.state.landmarks.append(
            LandmarkNode(lm_idx, landmark_id, position.copy())
        )
        self.state.visual_factors.append(
            VisualFactorData(pose_i, lm_idx, uv.copy(), sqrt_info)
        )
        self._enforce_limits()
        return lm_idx

    def add_loop_closure(
        self,
        pose_i: int,
        pose_j: int,
        delta_p: NDArray[np.float64],
        delta_R: NDArray[np.float64],
    ) -> None:
        self.state.loop_factors.append(
            LoopFactorData(pose_i, pose_j, delta_p.copy(), delta_R.copy())
        )

    def optimize(self) -> OptimizationReport:
        pose_states = [
            pose_to_vector(p.position, p.rotation) for p in self.state.poses
        ]
        lm_states = [lm.position.copy() for lm in self.state.landmarks]

        report = self.optimizer.optimize(
            pose_states,
            lm_states,
            self.state.imu_factors,
            self.state.visual_factors,
            self.state.loop_factors,
            self.intrinsics,
        )

        for i, p in enumerate(self.state.poses):
            pos, rot = vector_to_pose(report.pose_states[i])
            p.position = pos
            p.rotation = rot

        for j, lm in enumerate(self.state.landmarks):
            lm.position = report.landmark_states[j].copy()

        self.state.last_optimization = report
        return report

    def marginalize_old_poses(self, keep: int | None = None) -> None:
        """Remove oldest poses from window (retrospective correction keeps optimized values)."""
        keep_n = keep or self.max_poses
        if len(self.state.poses) <= keep_n:
            return

        drop = len(self.state.poses) - keep_n
        self.state.poses = self.state.poses[drop:]
        for i, p in enumerate(self.state.poses):
            p.index = i

        self._reindex_factors(drop)
        self._prune_orphan_landmarks()

    def memory_usage(self) -> MemoryReport:
        n_p = len(self.state.poses)
        n_l = len(self.state.landmarks)
        n_f = (
            len(self.state.imu_factors)
            + len(self.state.visual_factors)
            + len(self.state.loop_factors)
        )
        used = n_p * BYTES_PER_POSE + n_l * BYTES_PER_LANDMARK + n_f * BYTES_PER_FACTOR
        return MemoryReport(used, self.memory_budget_bytes, n_p, n_l, n_f)

    def _enforce_limits(self) -> None:
        while len(self.state.poses) > self.max_poses:
            self.marginalize_old_poses(self.max_poses)

        while len(self.state.landmarks) > self.max_landmarks:
            self.state.landmarks.pop(0)
            self._reindex_landmarks()

        while not self.memory_usage().within_budget and len(self.state.poses) > 2:
            self.marginalize_old_poses(len(self.state.poses) - 1)

    def _reindex_factors(self, pose_offset: int) -> None:
        def shift(factors, attr_i, attr_j=None):
            kept = []
            for f in factors:
                i = getattr(f, attr_i) - pose_offset
                j = getattr(f, attr_j) - pose_offset if attr_j else None
                if i < 0 or (attr_j and j is not None and j < 0):
                    continue
                if attr_j:
                    kept.append(type(f)(i, j, *[v for k, v in f.__dict__.items() if k not in (attr_i, attr_j)]))
                else:
                    kept.append(f)
            return kept

        self.state.imu_factors = [
            IMUFactorData(f.pose_i - pose_offset, f.pose_j - pose_offset, f.delta_p, f.delta_R, f.sqrt_info)
            for f in self.state.imu_factors
            if f.pose_i >= pose_offset and f.pose_j >= pose_offset
        ]
        self.state.visual_factors = [
            VisualFactorData(f.pose_i - pose_offset, f.landmark_j, f.uv, f.sqrt_info)
            for f in self.state.visual_factors
            if f.pose_i >= pose_offset
        ]
        self.state.loop_factors = [
            LoopFactorData(f.pose_i - pose_offset, f.pose_j - pose_offset, f.delta_p, f.delta_R, f.sqrt_info)
            for f in self.state.loop_factors
            if f.pose_i >= pose_offset and f.pose_j >= pose_offset
        ]

    def _reindex_landmarks(self) -> None:
        for j, lm in enumerate(self.state.landmarks):
            lm.index = j
        self.state.visual_factors = [
            VisualFactorData(f.pose_i, max(0, f.landmark_j - 1), f.uv, f.sqrt_info)
            for f in self.state.visual_factors
            if f.landmark_j > 0
        ]

    def _prune_orphan_landmarks(self) -> None:
        active_lm = {f.landmark_j for f in self.state.visual_factors}
        self.state.landmarks = [lm for lm in self.state.landmarks if lm.index in active_lm]
