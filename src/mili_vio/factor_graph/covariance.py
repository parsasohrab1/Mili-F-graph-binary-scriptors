"""Covariance and uncertainty extraction from factor graph."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.spatial.transform import Rotation


def estimate_pose_covariance(
    pose_states: list[NDArray[np.float64]],
    landmark_states: list[NDArray[np.float64]],
    imu_factors: list,
    visual_factors: list,
    loop_factors: list,
    intrinsics,
    pose_index: int = -1,
) -> NDArray[np.float64]:
    """
    Fast diagonal covariance approximation from factor information.

    Full numerical Hessian is too slow for real-time; this provides
    a conservative estimate suitable for uncertainty gating (Phase 4).
    """
    _ = landmark_states, imu_factors, visual_factors, loop_factors, intrinsics
    idx = pose_index if pose_index >= 0 else len(pose_states) - 1
    if idx < 0 or not pose_states:
        return np.eye(6) * 0.1

    n_obs = len(visual_factors) + len(imu_factors) + len(loop_factors)
    base_pos_var = max(0.01, 0.5 / max(n_obs, 1))
    base_rot_var = max(0.001, 0.1 / max(n_obs, 1))

    # Loop closures reduce uncertainty (retrospective correction)
    loop_factor = 0.5 if loop_factors else 1.0

    return np.diag([
        base_pos_var * loop_factor,
        base_pos_var * loop_factor,
        base_pos_var * loop_factor * 1.2,
        base_rot_var,
        base_rot_var,
        base_rot_var * 1.5,
    ])


def uncertainty_metric(covariance: NDArray[np.float64]) -> float:
    """Scalar uncertainty from position block of covariance (for Phase 4 sharing)."""
    pos_cov = covariance[:3, :3]
    return float(np.sqrt(np.trace(pos_cov) / 3.0))


def orientation_error_deg(
    estimated_rot: NDArray[np.float64],
    true_rot: NDArray[np.float64],
) -> float:
    r_err = Rotation.from_matrix(true_rot.T @ estimated_rot).as_rotvec()
    return float(np.degrees(np.linalg.norm(r_err)))
