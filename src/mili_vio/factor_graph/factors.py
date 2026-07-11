"""Camera projection and factor residual functions."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.spatial.transform import Rotation

from mili_vio.vio.backend.pose_utils import relative_pose, vector_to_pose
from mili_vio.vio.datasets.base import CameraIntrinsics


def project_landmark(
    pose_vec: NDArray[np.float64],
    landmark: NDArray[np.float64],
    intrinsics: CameraIntrinsics,
) -> NDArray[np.float64]:
    position, rotation = vector_to_pose(pose_vec)
    p_cam = rotation.T @ (landmark - position)
    if p_cam[2] <= 1e-6:
        p_cam[2] = 1e-6
    u = intrinsics.fx * p_cam[0] / p_cam[2] + intrinsics.cx
    v = intrinsics.fy * p_cam[1] / p_cam[2] + intrinsics.cy
    return np.array([u, v])


def reprojection_residual(
    pose_vec: NDArray[np.float64],
    landmark: NDArray[np.float64],
    measured_uv: NDArray[np.float64],
    intrinsics: CameraIntrinsics,
    sqrt_info: float = 1.0,
) -> NDArray[np.float64]:
    projected = project_landmark(pose_vec, landmark, intrinsics)
    return sqrt_info * (projected - measured_uv)


def imu_factor_residual(
    pose_i: NDArray[np.float64],
    pose_j: NDArray[np.float64],
    delta_p: NDArray[np.float64],
    delta_R: NDArray[np.float64],
    sqrt_info: float = 8.0,
) -> NDArray[np.float64]:
    pos_i, rot_i = vector_to_pose(pose_i)
    pos_j, rot_j = vector_to_pose(pose_j)
    est_p, est_R = relative_pose(pos_i, rot_i, pos_j, rot_j)
    pos_err = est_p - delta_p
    rot_err = Rotation.from_matrix(delta_R.T @ est_R).as_rotvec()
    return sqrt_info * np.concatenate([pos_err, rot_err])


def loop_closure_residual(
    pose_i: NDArray[np.float64],
    pose_j: NDArray[np.float64],
    measured_p: NDArray[np.float64],
    measured_R: NDArray[np.float64],
    sqrt_info: float = 15.0,
) -> NDArray[np.float64]:
    pos_i, rot_i = vector_to_pose(pose_i)
    pos_j, rot_j = vector_to_pose(pose_j)
    est_p, est_R = relative_pose(pos_i, rot_i, pos_j, rot_j)
    pos_err = est_p - measured_p
    rot_err = Rotation.from_matrix(measured_R.T @ est_R).as_rotvec()
    return sqrt_info * np.concatenate([pos_err, rot_err])


def triangulate_landmark(
    pose_a: NDArray[np.float64],
    pose_b: NDArray[np.float64],
    uv_a: NDArray[np.float64],
    uv_b: NDArray[np.float64],
    intrinsics: CameraIntrinsics,
    depth: float = 3.0,
) -> NDArray[np.float64]:
    """Initialize landmark via midpoint in front of first camera."""
    pos_a, rot_a = vector_to_pose(pose_a)
    ray = np.array([
        (uv_a[0] - intrinsics.cx) / intrinsics.fx,
        (uv_a[1] - intrinsics.cy) / intrinsics.fy,
        1.0,
    ])
    ray /= np.linalg.norm(ray)
    point_cam = ray * depth
    return pos_a + rot_a @ point_cam
