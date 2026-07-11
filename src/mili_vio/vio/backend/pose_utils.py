"""SE(3) pose utilities for factor-graph optimization."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.spatial.transform import Rotation


def pose_to_vector(position: NDArray[np.float64], rotation: NDArray[np.float64]) -> NDArray[np.float64]:
    rvec = Rotation.from_matrix(rotation).as_rotvec()
    return np.concatenate([position, rvec])


def vector_to_pose(x: NDArray[np.float64]) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    position = x[:3].copy()
    rotation = Rotation.from_rotvec(x[3:6]).as_matrix()
    return position, rotation


def relative_pose(
    pos_i: NDArray[np.float64],
    rot_i: NDArray[np.float64],
    pos_j: NDArray[np.float64],
    rot_j: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    rot_ij = rot_i.T @ rot_j
    pos_ij = rot_i.T @ (pos_j - pos_i)
    return pos_ij, rot_ij


def pose_residual(
    x_i: NDArray[np.float64],
    x_j: NDArray[np.float64],
    measured_pos: NDArray[np.float64],
    measured_rot: NDArray[np.float64],
    sqrt_info: float = 10.0,
) -> NDArray[np.float64]:
    pos_i, rot_i = vector_to_pose(x_i)
    pos_j, rot_j = vector_to_pose(x_j)
    est_pos, est_rot = relative_pose(pos_i, rot_i, pos_j, rot_j)

    pos_err = est_pos - measured_pos
    rot_err = Rotation.from_matrix(measured_rot.T @ est_rot).as_rotvec()

    return sqrt_info * np.concatenate([pos_err, rot_err])
