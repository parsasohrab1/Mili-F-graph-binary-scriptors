"""SciPy-based factor graph backend (desktop, cross-platform)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from mili_vio.vio.backend.pose_utils import pose_residual, pose_to_vector, relative_pose, vector_to_pose
from mili_vio.vio.imu_preintegration import IMUPreintegrated


@dataclass
class PoseNode:
    index: int
    timestamp_ns: int
    position: NDArray[np.float64]
    rotation: NDArray[np.float64]


@dataclass
class RelativePoseFactor:
    i: int
    j: int
    measured_position: NDArray[np.float64]
    measured_rotation: NDArray[np.float64]
    information: float = 10.0


@dataclass
class IMUFactor:
    i: int
    j: int
    preintegrated: IMUPreintegrated
    information: float = 5.0


@dataclass
class LoopClosureFactor:
    i: int
    j: int
    measured_position: NDArray[np.float64]
    measured_rotation: NDArray[np.float64]
    information: float = 20.0


@dataclass
class OptimizationResult:
    poses: list[PoseNode]
    optimization_time_ms: float
    final_cost: float
    iterations: int
    backend: str = "scipy_factor_graph"


class ScipyFactorGraph:
    """Nonlinear factor-graph optimizer using scipy.optimize.least_squares."""

    def __init__(self) -> None:
        self.poses: list[PoseNode] = []
        self.relative_factors: list[RelativePoseFactor] = []
        self.imu_factors: list[IMUFactor] = []
        self.loop_factors: list[LoopClosureFactor] = []

    def add_pose(self, timestamp_ns: int, position: NDArray[np.float64], rotation: NDArray[np.float64]) -> int:
        idx = len(self.poses)
        self.poses.append(PoseNode(index=idx, timestamp_ns=timestamp_ns, position=position.copy(), rotation=rotation.copy()))
        return idx

    def add_relative_factor(self, i: int, j: int, measured_pos: NDArray[np.float64], measured_rot: NDArray[np.float64], info: float = 10.0) -> None:
        self.relative_factors.append(RelativePoseFactor(i, j, measured_pos.copy(), measured_rot.copy(), info))

    def add_imu_factor(self, i: int, j: int, preint: IMUPreintegrated) -> None:
        if preint.dt <= 0:
            return
        delta_rot = preint.delta_R
        self.relative_factors.append(
            RelativePoseFactor(i, j, preint.delta_p.copy(), delta_rot.copy(), information=5.0)
        )
        self.imu_factors.append(IMUFactor(i, j, preint))

    def add_loop_closure(self, i: int, j: int, measured_pos: NDArray[np.float64], measured_rot: NDArray[np.float64]) -> None:
        self.loop_factors.append(LoopClosureFactor(i, j, measured_pos.copy(), measured_rot.copy()))

    def optimize(self, max_iterations: int = 20) -> OptimizationResult:
        if len(self.poses) < 2:
            return OptimizationResult(
                poses=self.poses,
                optimization_time_ms=0.0,
                final_cost=0.0,
                iterations=0,
            )

        x0 = np.concatenate([pose_to_vector(p.position, p.rotation) for p in self.poses])
        factors = self.relative_factors + [
            RelativePoseFactor(f.i, f.j, f.measured_position, f.measured_rotation, f.information)
            for f in self.loop_factors
        ]

        start = time.perf_counter()

        def residuals(x: NDArray[np.float64]) -> NDArray[np.float64]:
            res_list: list[NDArray[np.float64]] = []
            n = len(self.poses)
            for f in factors:
                if f.i >= n or f.j >= n:
                    continue
                xi = x[f.i * 6 : (f.i + 1) * 6]
                xj = x[f.j * 6 : (f.j + 1) * 6]
                res_list.append(pose_residual(xi, xj, f.measured_position, f.measured_rotation, f.information))
            if not res_list:
                return np.zeros(1)
            return np.concatenate(res_list)

        # Fix first pose
        def residuals_fixed(x_free: NDArray[np.float64]) -> NDArray[np.float64]:
            x_full = np.zeros(len(self.poses) * 6)
            x_full[:6] = x0[:6]
            x_full[6:] = x_free
            return residuals(x_full)

        result = least_squares(
            residuals_fixed,
            x0[6:],
            method="lm",
            max_nfev=max_iterations * len(factors) * 6,
        )

        x_opt = np.zeros(len(self.poses) * 6)
        x_opt[:6] = x0[:6]
        x_opt[6:] = result.x

        optimized: list[PoseNode] = []
        for i, pose in enumerate(self.poses):
            pos, rot = vector_to_pose(x_opt[i * 6 : (i + 1) * 6])
            optimized.append(PoseNode(pose.index, pose.timestamp_ns, pos, rot))

        elapsed_ms = (time.perf_counter() - start) * 1000
        return OptimizationResult(
            poses=optimized,
            optimization_time_ms=elapsed_ms,
            final_cost=float(result.cost),
            iterations=result.nfev,
        )


def estimate_visual_odometry(
    matches_count: int,
    focal: float,
    avg_parallax_px: float = 2.0,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Estimate relative pose from 2D feature matches (simplified VO)."""
    depth = 1.0
    trans_norm = avg_parallax_px / focal * depth
    trans = np.array([trans_norm, 0.0, 0.0])
    rot = Rotation.from_rotvec(np.array([0.0, 0.0, 0.001 * matches_count])).as_matrix()
    return trans, rot
