"""Synthetic VIO dataset for testing without external downloads."""

from __future__ import annotations

import cv2
import numpy as np
from scipy.spatial.transform import Rotation

from mili_vio.vio.datasets.base import (
    CameraFrame,
    CameraIntrinsics,
    DatasetType,
    GroundTruthPose,
    IMUSample,
    VIODataset,
)


def _make_checkerboard(width: int, height: int, block: int = 40) -> np.ndarray:
    img = np.zeros((height, width), dtype=np.uint8)
    for y in range(0, height, block):
        for x in range(0, width, block):
            if ((x // block) + (y // block)) % 2 == 0:
                img[y : y + block, x : x + block] = 220
    return img


def generate_synthetic(
    num_frames: int = 120,
    width: int = 640,
    height: int = 480,
    seed: int = 42,
) -> VIODataset:
    """Generate a synthetic trajectory with textured images and IMU."""
    rng = np.random.default_rng(seed)
    intrinsics = CameraIntrinsics(fx=500.0, fy=500.0, cx=width / 2, cy=height / 2, width=width, height=height)
    base_texture = _make_checkerboard(width, height)

    # Circular trajectory with varying altitude
    frames: list[CameraFrame] = []
    imu_samples: list[IMUSample] = []
    ground_truth: list[GroundTruthPose] = []

    t_ns = 1_700_000_000_000_000
    dt_ns = 33_333_333  # ~30 Hz

    for i in range(num_frames):
        angle = i * 0.05
        pos = np.array([3.0 * np.cos(angle), 3.0 * np.sin(angle), 1.0 + 0.3 * np.sin(angle * 2)])
        yaw = angle + np.pi / 2
        quat = Rotation.from_euler("zyx", [yaw, 0.05 * np.sin(angle), 0.0]).as_quat()  # x,y,z,w
        quat_wxyz = np.array([quat[3], quat[0], quat[1], quat[2]])

        ts = t_ns + i * dt_ns

        # Simulate camera motion via image warp
        dx = int(10 * np.cos(angle))
        dy = int(10 * np.sin(angle))
        M = np.float32([[1, 0, dx], [0, 1, dy]])
        image = cv2.warpAffine(base_texture, M, (width, height), borderMode=cv2.BORDER_REFLECT)
        noise = rng.integers(0, 20, image.shape, dtype=np.uint8)
        image = cv2.add(image, noise)

        frames.append(CameraFrame(timestamp_ns=ts, image=image, frame_id=i))
        ground_truth.append(GroundTruthPose(timestamp_ns=ts, position=pos.copy(), quaternion=quat_wxyz.copy()))

        # IMU at 200 Hz between frames
        for j in range(6):
            imu_ts = ts + j * (dt_ns // 6)
            imu_samples.append(
                IMUSample(
                    timestamp_ns=imu_ts,
                    gyro=rng.normal(0, 0.01, 3) + np.array([0, 0, 0.05]),
                    accel=rng.normal(0, 0.05, 3) + np.array([0, 0, 9.81]),
                )
            )

    return VIODataset(
        name="synthetic",
        dataset_type=DatasetType.SYNTHETIC,
        intrinsics=intrinsics,
        frames=frames,
        imu=imu_samples,
        ground_truth=ground_truth,
    )
