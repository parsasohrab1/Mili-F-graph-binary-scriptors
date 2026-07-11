"""Dataset loader factory."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from mili_vio.vio.datasets.base import CameraIntrinsics, DatasetType, VIODataset
from mili_vio.vio.datasets.euroc import load_euroc
from mili_vio.vio.datasets.synthetic import generate_synthetic
from mili_vio.vio.datasets.tum_vi import load_tum_vi


def load_phase1_config(path: Optional[Path] = None) -> dict:
    if path is None:
        path = Path(__file__).resolve().parents[4] / "configs" / "phase1.yaml"
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_dataset(
    name: str = "synthetic",
    dataset_root: Optional[Path] = None,
    max_frames: Optional[int] = None,
    config: Optional[dict] = None,
) -> VIODataset:
    cfg = config or load_phase1_config()
    p1 = cfg.get("phase1", {})
    root = dataset_root or Path(p1.get("dataset_root", "data/datasets"))
    limit = max_frames or p1.get("max_frames", 500)

    cam_cfg = p1.get("camera", {})
    intrinsics = CameraIntrinsics(
        fx=cam_cfg.get("fx", 458.654),
        fy=cam_cfg.get("fy", 457.296),
        cx=cam_cfg.get("cx", 367.215),
        cy=cam_cfg.get("cy", 248.375),
    )

    if name == "synthetic":
        return generate_synthetic(num_frames=min(limit, 120))

    euroc_path = root / "euroc" / name
    if euroc_path.exists():
        return load_euroc(euroc_path, max_frames=limit, intrinsics=intrinsics)

    tum_path = root / "tum_vi" / name
    if tum_path.exists():
        return load_tum_vi(tum_path, max_frames=limit)

    raise FileNotFoundError(
        f"Dataset '{name}' not found. Place EuRoC/TUM-VI under {root} or use name='synthetic'."
    )
