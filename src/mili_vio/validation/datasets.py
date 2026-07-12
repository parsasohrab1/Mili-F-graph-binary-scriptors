"""EuRoC / TUM-VI presence checks and optional download."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.request import urlretrieve

from mili_vio.validation.config import phase6_section

# Public dataset mirrors (manual download also documented in docs/PHASE6_VALIDATION.md)
EUROC_DOWNLOAD_URLS: dict[str, str] = {
    "MH_01_easy": (
        "http://robotics.ethz.ch/~asl-datasets/ijrr_euroc_mav_dataset/"
        "machine_hall/MH_01_easy/MH_01_easy.zip"
    ),
    "MH_02_easy": (
        "http://robotics.ethz.ch/~asl-datasets/ijrr_euroc_mav_dataset/"
        "machine_hall/MH_02_easy/MH_02_easy.zip"
    ),
    "V1_01_easy": (
        "http://robotics.ethz.ch/~asl-datasets/ijrr_euroc_mav_dataset/"
        "vignettes/V1_01_easy/V1_01_easy.zip"
    ),
}

TUM_VI_DOWNLOAD_URLS: dict[str, str] = {
    "dataset-room1_512_16": (
        "https://vision.in.tum.de/rgbd/dataset/vi-room1/dataset-room1_512_16.zip"
    ),
}


@dataclass
class DatasetPresence:
    name: str
    kind: str
    path: Path
    present: bool
    has_ground_truth: bool = False


@dataclass
class DatasetSuiteStatus:
    root: Path
    datasets: list[DatasetPresence] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def all_present(self) -> bool:
        return len(self.missing) == 0


def _euroc_present(root: Path, name: str) -> DatasetPresence:
    seq = root / "euroc" / name
    cam_csv = seq / "mav0" / "cam0" / "data.csv"
    gt = seq / "mav0" / "state_groundtruth_estimate0" / "data.csv"
    return DatasetPresence(
        name=name,
        kind="euroc",
        path=seq,
        present=cam_csv.exists(),
        has_ground_truth=gt.exists(),
    )


def _tum_present(root: Path, name: str) -> DatasetPresence:
    seq = root / "tum_vi" / name
    cam_csv = seq / "cam0" / "data.csv"
    gt = seq / "groundtruth.txt"
    return DatasetPresence(
        name=name,
        kind="tum_vi",
        path=seq,
        present=cam_csv.exists(),
        has_ground_truth=gt.exists(),
    )


def check_datasets(
    dataset_root: Optional[Path] = None,
    config: Optional[dict] = None,
) -> DatasetSuiteStatus:
    p6 = phase6_section(config)
    root = Path(dataset_root or p6.get("dataset_root", "data/datasets"))
    ds_cfg = p6.get("datasets", {})

    status = DatasetSuiteStatus(root=root)
    for name in ds_cfg.get("euroc_sequences", []):
        entry = _euroc_present(root, name)
        status.datasets.append(entry)
        if not entry.present:
            status.missing.append(f"euroc/{name}")

    for name in ds_cfg.get("tum_vi_sequences", []):
        entry = _tum_present(root, name)
        status.datasets.append(entry)
        if not entry.present:
            status.missing.append(f"tum_vi/{name}")

    if status.missing:
        status.notes.append(
            "Run: python scripts/download_datasets.py --download "
            f"(root={root})"
        )
    return status


def _extract_zip(zip_path: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)


def download_sequence(
    name: str,
    kind: str,
    dataset_root: Path,
    force: bool = False,
) -> tuple[bool, str]:
    """Download and extract one sequence. Returns (success, message)."""
    if kind == "euroc":
        url = EUROC_DOWNLOAD_URLS.get(name)
        dest_parent = dataset_root / "euroc"
    elif kind == "tum_vi":
        url = TUM_VI_DOWNLOAD_URLS.get(name)
        dest_parent = dataset_root / "tum_vi"
    else:
        return False, f"Unknown kind: {kind}"

    if not url:
        return False, f"No download URL configured for {kind}/{name}"

    present = check_datasets(dataset_root).datasets
    if any(d.name == name and d.present for d in present) and not force:
        return True, f"{name} already present"

    dest_parent.mkdir(parents=True, exist_ok=True)
    zip_path = dest_parent / f"{name}.zip"
    try:
        print(f"Downloading {name} from {url} ...")
        urlretrieve(url, zip_path)
        _extract_zip(zip_path, dest_parent)
        zip_path.unlink(missing_ok=True)
        return True, f"Downloaded {kind}/{name}"
    except OSError as exc:
        return False, f"Download failed for {name}: {exc}"


def download_all_datasets(
    dataset_root: Optional[Path] = None,
    config: Optional[dict] = None,
    force: bool = False,
) -> list[str]:
    """Download all configured sequences. Returns list of status messages."""
    p6 = phase6_section(config)
    root = Path(dataset_root or p6.get("dataset_root", "data/datasets"))
    ds_cfg = p6.get("datasets", {})
    messages: list[str] = []

    for name in ds_cfg.get("euroc_sequences", []):
        ok, msg = download_sequence(name, "euroc", root, force=force)
        messages.append(msg)

    for name in ds_cfg.get("tum_vi_sequences", []):
        ok, msg = download_sequence(name, "tum_vi", root, force=force)
        messages.append(msg)

    return messages
