#!/usr/bin/env python3
"""Download EuRoC / TUM-VI sequences for Phase 6 validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as script without install
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mili_vio.validation.datasets import (  # noqa: E402
    check_datasets,
    download_all_datasets,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="EuRoC / TUM-VI dataset helper")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check which sequences are present (default)",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download missing sequences (large files, requires network)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if sequence exists",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("data/datasets"),
        help="Dataset root directory",
    )
    args = parser.parse_args()

    if args.download:
        messages = download_all_datasets(dataset_root=args.root, force=args.force)
        for msg in messages:
            print(msg)
        status = check_datasets(dataset_root=args.root)
        sys.exit(0 if status.all_present else 1)

    status = check_datasets(dataset_root=args.root)
    print(f"Dataset root: {status.root.resolve()}")
    for ds in status.datasets:
        mark = "OK" if ds.present else "MISSING"
        gt = "ground_truth" if ds.has_ground_truth else "no_gt"
        print(f"  [{mark}] {ds.kind}/{ds.name} ({gt})")

    if status.missing:
        print(f"\nMissing ({len(status.missing)}): {', '.join(status.missing)}")
        print("Download: python scripts/download_datasets.py --download")
        sys.exit(1)

    print("\nAll configured sequences present.")
    sys.exit(0)


if __name__ == "__main__":
    main()
