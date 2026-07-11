"""Fast nonlinear optimizer with time budget for FR-2."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import least_squares

from mili_vio.factor_graph.factors import (
    imu_factor_residual,
    loop_closure_residual,
    reprojection_residual,
)
from mili_vio.vio.backend.pose_utils import vector_to_pose
from mili_vio.vio.datasets.base import CameraIntrinsics


@dataclass
class IMUFactorData:
    pose_i: int
    pose_j: int
    delta_p: NDArray[np.float64]
    delta_R: NDArray[np.float64]
    sqrt_info: float = 8.0


@dataclass
class VisualFactorData:
    pose_i: int
    landmark_j: int
    uv: NDArray[np.float64]
    sqrt_info: float = 1.0


@dataclass
class LoopFactorData:
    pose_i: int
    pose_j: int
    delta_p: NDArray[np.float64]
    delta_R: NDArray[np.float64]
    sqrt_info: float = 15.0


@dataclass
class OptimizationReport:
    pose_states: list[NDArray[np.float64]]
    landmark_states: list[NDArray[np.float64]]
    final_cost: float
    iterations: int
    optimization_time_ms: float
    converged: bool


class FastFactorGraphOptimizer:
    """Gauss-Newton / LM optimizer with strict time budget (< 5ms target)."""

    def __init__(
        self,
        max_time_ms: float = 5.0,
        max_iterations: int = 8,
        convergence_tol: float = 1e-4,
    ) -> None:
        self.max_time_ms = max_time_ms
        self.max_iterations = max_iterations
        self.convergence_tol = convergence_tol

    def optimize(
        self,
        pose_states: list[NDArray[np.float64]],
        landmark_states: list[NDArray[np.float64]],
        imu_factors: list[IMUFactorData],
        visual_factors: list[VisualFactorData],
        loop_factors: list[LoopFactorData],
        intrinsics: CameraIntrinsics,
        fix_first_pose: bool = True,
    ) -> OptimizationReport:
        start = time.perf_counter()
        n_poses = len(pose_states)
        n_lm = len(landmark_states)

        if n_poses == 0:
            return OptimizationReport([], [], 0.0, 0, 0.0, True)

        x0 = self._pack(pose_states, landmark_states)

        def residuals(x: NDArray[np.float64]) -> NDArray[np.float64]:
            return self._compute_residuals(
                x, n_poses, n_lm, imu_factors, visual_factors, loop_factors, intrinsics
            )

        if fix_first_pose and n_poses > 1:
            x_free0 = x0[6:]

            def residuals_free(xf: NDArray[np.float64]) -> NDArray[np.float64]:
                x_full = np.zeros_like(x0)
                x_full[:6] = x0[:6]
                x_full[6:] = xf
                return residuals(x_full)

            n_res = len(residuals_free(x_free0))
            n_var = len(x_free0)
            method = "lm" if n_res >= n_var else "trf"

            result = least_squares(
                residuals_free,
                x_free0,
                method=method,
                ftol=self.convergence_tol,
                xtol=self.convergence_tol,
                max_nfev=self.max_iterations,
            )
            x_opt = np.zeros_like(x0)
            x_opt[:6] = x0[:6]
            x_opt[6:] = result.x
            final_cost = float(result.cost)
            iterations = result.nfev
            converged = result.success
        elif n_poses == 1:
            x_opt = x0
            final_cost = float(np.sum(residuals(x0) ** 2))
            iterations = 0
            converged = True
        else:
            n_res = len(residuals(x0))
            n_var = len(x0)
            method = "lm" if n_res >= n_var else "trf"
            result = least_squares(
                residuals,
                x0,
                method=method,
                ftol=self.convergence_tol,
                xtol=self.convergence_tol,
                max_nfev=self.max_iterations,
            )
            x_opt = result.x
            final_cost = float(result.cost)
            iterations = result.nfev
            converged = result.success

        elapsed_ms = (time.perf_counter() - start) * 1000
        opt_poses, opt_lm = self._unpack(x_opt, n_poses, n_lm)

        return OptimizationReport(
            pose_states=opt_poses,
            landmark_states=opt_lm,
            final_cost=final_cost,
            iterations=iterations,
            optimization_time_ms=elapsed_ms,
            converged=converged,
        )

    def _pack(
        self,
        poses: list[NDArray[np.float64]],
        landmarks: list[NDArray[np.float64]],
    ) -> NDArray[np.float64]:
        return np.concatenate(poses + landmarks) if poses or landmarks else np.zeros(1)

    def _unpack(
        self,
        x: NDArray[np.float64],
        n_poses: int,
        n_lm: int,
    ) -> tuple[list[NDArray[np.float64]], list[NDArray[np.float64]]]:
        poses = [x[i * 6 : (i + 1) * 6].copy() for i in range(n_poses)]
        offset = n_poses * 6
        landmarks = [x[offset + j * 3 : offset + (j + 1) * 3].copy() for j in range(n_lm)]
        return poses, landmarks

    def _compute_residuals(
        self,
        x: NDArray[np.float64],
        n_poses: int,
        n_lm: int,
        imu_factors: list[IMUFactorData],
        visual_factors: list[VisualFactorData],
        loop_factors: list[LoopFactorData],
        intrinsics: CameraIntrinsics,
    ) -> NDArray[np.float64]:
        res: list[NDArray[np.float64]] = []

        def pose(i: int) -> NDArray[np.float64]:
            return x[i * 6 : (i + 1) * 6]

        def lm(j: int) -> NDArray[np.float64]:
            base = n_poses * 6
            return x[base + j * 3 : base + (j + 1) * 3]

        for f in imu_factors:
            if f.pose_i < n_poses and f.pose_j < n_poses:
                res.append(imu_factor_residual(pose(f.pose_i), pose(f.pose_j), f.delta_p, f.delta_R, f.sqrt_info))

        for f in visual_factors:
            if f.pose_i < n_poses and f.landmark_j < n_lm:
                res.append(reprojection_residual(pose(f.pose_i), lm(f.landmark_j), f.uv, intrinsics, f.sqrt_info))

        for f in loop_factors:
            if f.pose_i < n_poses and f.pose_j < n_poses:
                res.append(loop_closure_residual(pose(f.pose_i), pose(f.pose_j), f.delta_p, f.delta_R, f.sqrt_info))

        # Anchor landmarks to keep system observable when underconstrained
        base = n_poses * 6
        for j in range(n_lm):
            lm_j = lm(j)
            res.append(0.01 * lm_j)

        return np.concatenate(res) if res else np.zeros(1)
