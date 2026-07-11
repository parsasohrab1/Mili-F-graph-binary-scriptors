"""EuRoC MAV dataset loader."""

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


def _load_csv_timestamps(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, comment="#")


def load_euroc(
    sequence_path: Path,
    max_frames: int | None = None,
    intrinsics: CameraIntrinsics | None = None,
) -> VIODataset:
    """
    Load EuRoC MAV sequence.

    Expected layout::
        sequence_path/mav0/cam0/data.csv
        sequence_path/mav0/cam0/data/*.png
        sequence_path/mav0/imu0/data.csv
        sequence_path/mav0/state_groundtruth_estimate0/data.csv
    """
    cam_dir = sequence_path / "mav0" / "cam0"
    imu_path = sequence_path / "mav0" / "imu0" / "data.csv"
    gt_path = sequence_path / "mav0" / "state_groundtruth_estimate0" / "data.csv"
    cam_csv = cam_dir / "data.csv"

    if not cam_csv.exists():
        raise FileNotFoundError(f"EuRoC sequence not found: {cam_csv}")

    cam_df = _load_csv_timestamps(cam_csv)
    frames: list[CameraFrame] = []
    limit = max_frames or len(cam_df)

    for i, row in cam_df.head(limit).iterrows():
        ts = int(row["#timestamp [ns]"] if "#timestamp [ns]" in row else row.iloc[0])
        img_path = cam_dir / "data" / f"{ts}.png"
        if not img_path.exists():
            continue
        image = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            continue
        frames.append(CameraFrame(timestamp_ns=ts, image=image, frame_id=len(frames)))

    imu_samples: list[IMUSample] = []
    if imu_path.exists():
        imu_df = _load_csv_timestamps(imu_path)
        for _, row in imu_df.iterrows():
            ts = int(row["#timestamp [ns]"])
            imu_samples.append(
                IMUSample(
                    timestamp_ns=ts,
                    gyro=np.array([row["w_RS_S_x [rad s-1]"], row["w_RS_S_y [rad s-1]"], row["w_RS_S_z [rad s-1]"]]),
                    accel=np.array([row["a_RS_S_x [m s-2]"], row["a_RS_S_y [m s-2]"], row["a_RS_S_z [m s-2]"]]),
                )
            )

    ground_truth: list[GroundTruthPose] = []
    if gt_path.exists():
        gt_df = _load_csv_timestamps(gt_path)
        for _, row in gt_df.iterrows():
            ground_truth.append(
                GroundTruthPose(
                    timestamp_ns=int(row["#timestamp"]),
                    position=np.array([row["p_RS_R_x [m]"], row["p_RS_R_y [m]"], row["p_RS_R_z [m]"]]),
                    quaternion=np.array([
                        row["q_RS_w []"],
                        row["q_RS_x []"],
                        row["q_RS_y []"],
                        row["q_RS_z []"],
                    ]),
                )
            )

    if intrinsics is None:
        intrinsics = CameraIntrinsics(fx=458.654, fy=457.296, cx=367.215, cy=248.375)

    return VIODataset(
        name=sequence_path.name,
        dataset_type=DatasetType.EUROC,
        intrinsics=intrinsics,
        frames=frames,
        imu=imu_samples,
        ground_truth=ground_truth,
    )
