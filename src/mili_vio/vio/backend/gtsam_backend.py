"""Optional GTSAM backend (Linux/macOS when gtsam is installed)."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from mili_vio.vio.backend.scipy_backend import OptimizationResult, PoseNode, ScipyFactorGraph
from mili_vio.vio.imu_preintegration import IMUPreintegrated

try:
    import gtsam
    from gtsam import (
        BetweenFactorPose3,
        NonlinearFactorGraph,
        Pose3,
        PriorFactorPose3,
        Rot3,
        Values,
    )

    HAS_GTSAM = True
except ImportError:
    HAS_GTSAM = False


@dataclass
class GtsamFactorGraph:
    """GTSAM factor graph wrapper with SciPy fallback."""

    _fallback: ScipyFactorGraph
    _use_gtsam: bool

    def __init__(self) -> None:
        self._fallback = ScipyFactorGraph()
        self._use_gtsam = HAS_GTSAM

    def add_pose(self, timestamp_ns: int, position: NDArray[np.float64], rotation: NDArray[np.float64]) -> int:
        return self._fallback.add_pose(timestamp_ns, position, rotation)

    def add_relative_factor(self, i: int, j: int, measured_pos: NDArray[np.float64], measured_rot: NDArray[np.float64], info: float = 10.0) -> None:
        self._fallback.add_relative_factor(i, j, measured_pos, measured_rot, info)

    def add_imu_factor(self, i: int, j: int, preint: IMUPreintegrated) -> None:
        self._fallback.add_imu_factor(i, j, preint)

    def add_loop_closure(self, i: int, j: int, measured_pos: NDArray[np.float64], measured_rot: NDArray[np.float64]) -> None:
        self._fallback.add_loop_closure(i, j, measured_pos, measured_rot)

    def optimize(self, max_iterations: int = 20) -> OptimizationResult:
        if not self._use_gtsam or len(self._fallback.poses) < 2:
            result = self._fallback.optimize(max_iterations)
            result.backend = "scipy_factor_graph"
            return result

        start = time.perf_counter()
        graph = NonlinearFactorGraph()
        initial = Values()
        noise = gtsam.noiseModel.Diagonal.Sigmas(np.array([0.1] * 6))

        for pose in self._fallback.poses:
            rot = Rot3(rotation=pose.rotation)
            p = Pose3(rot, pose.position)
            initial.insert(pose.index, p)
            if pose.index == 0:
                graph.add(PriorFactorPose3(0, p, noise))

        between_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array([0.05] * 6))
        for f in self._fallback.relative_factors:
            rel = Pose3(Rot3(rotation=f.measured_rotation), f.measured_position)
            graph.add(BetweenFactorPose3(f.i, f.j, rel, between_noise))

        for f in self._fallback.loop_factors:
            rel = Pose3(Rot3(rotation=f.measured_rotation), f.measured_position)
            loop_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array([0.02] * 6))
            graph.add(BetweenFactorPose3(f.i, f.j, rel, loop_noise))

        params = gtsam.LevenbergMarquardtParams()
        params.setMaxIterations(max_iterations)
        optimizer = gtsam.LevenbergMarquardtOptimizer(graph, initial, params)
        solution = optimizer.optimize()

        optimized: list[PoseNode] = []
        for pose in self._fallback.poses:
            p = solution.atPose3(pose.index)
            optimized.append(
                PoseNode(
                    pose.index,
                    pose.timestamp_ns,
                    np.array(p.translation()).reshape(3),
                    np.array(p.rotation().matrix()),
                )
            )

        elapsed_ms = (time.perf_counter() - start) * 1000
        return OptimizationResult(
            poses=optimized,
            optimization_time_ms=elapsed_ms,
            final_cost=optimizer.error(),
            iterations=max_iterations,
            backend="gtsam",
        )


def create_factor_graph() -> GtsamFactorGraph:
    return GtsamFactorGraph()
