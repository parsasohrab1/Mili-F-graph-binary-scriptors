"""TUM-VI dataset loader."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from mili_vio.vio.datasets.base import (
    CameraFrame,
    CameraIntrinsics,
    DatasetType,
    GroundTruthPose,
    IMUSample,
    VIODataset,
)


def _read_data_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, comment="#", delim_whitespace=True, header=None)


def load_tum_vi(
    sequence_path: Path,
    max_frames: int | None = None,
    intrinsics: CameraIntrinsics | None = None,
) -> VIODataset:
    """
    Load TUM-VI sequence (cam0 + imu0 + groundtruth).

    Expected layout::
        sequence_path/cam0/data.csv
        sequence_path/cam0/data/*.png
        sequence_path/imu0/data.csv
        sequence_path/groundtruth/data.csv
    """
    cam_dir = sequence_path / "cam0"
    cam_csv = cam_dir / "data.csv"
    imu_path = sequence_path / "imu0" / "data.csv"
    gt_path = sequence_path / "groundtruth" / "data.csv"

    if not cam_csv.exists():
        raise FileNotFoundError(f"TUM-VI sequence not found: {cam_csv}")

    cam_df = _read_data_csv(cam_csv)
    cam_df.columns = ["timestamp", "filename"]
    frames: list[CameraFrame] = []
    limit = max_frames or len(cam_df)

    for _, row in cam_df.head(limit).iterrows():
        ts = int(row["timestamp"])
        img_path = cam_dir / "data" / row["filename"]
        if not img_path.exists():
            continue
        image = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            continue
        frames.append(CameraFrame(timestamp_ns=ts, image=image, frame_id=len(frames)))

    imu_samples: list[IMUSample] = []
    if imu_path.exists():
        imu_df = _read_data_csv(imu_path)
        imu_df.columns = ["timestamp", "wx", "wy", "wz", "ax", "ay", "az"]
        for _, row in imu_df.iterrows():
            imu_samples.append(
                IMUSample(
                    timestamp_ns=int(row["timestamp"]),
                    gyro=np.array([row["wx"], row["wy"], row["wz"]]),
                    accel=np.array([row["ax"], row["ay"], row["az"]]),
                )
            )

    ground_truth: list[GroundTruthPose] = []
    if gt_path.exists():
        gt_df = _read_data_csv(gt_path)
        gt_df.columns = ["timestamp", "tx", "ty", "tz", "qx", "qy", "qz", "qw"]
        for _, row in gt_df.iterrows():
            ground_truth.append(
                GroundTruthPose(
                    timestamp_ns=int(row["timestamp"]),
                    position=np.array([row["tx"], row["ty"], row["tz"]]),
                    quaternion=np.array([row["qw"], row["qx"], row["qy"], row["qz"]]),
                )
            )

    if intrinsics is None:
        intrinsics = CameraIntrinsics(fx=190.978, fy=190.973, cx=252.568, cy=254.753, width=512, height=512)

    return VIODataset(
        name=sequence_path.name,
        dataset_type=DatasetType.TUM_VI,
        intrinsics=intrinsics,
        frames=frames,
        imu=imu_samples,
        ground_truth=ground_truth,
    )
