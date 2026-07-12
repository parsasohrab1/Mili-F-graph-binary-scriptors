"""CLI for integrated end-to-end VIO runtime."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mili_vio.common.srs_constants import verify_embedded_alignment
from mili_vio.runtime.integrated_pipeline import run_integrated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mili VIO integrated runtime (FR-1 → FR-2 → FR-3 → FC output)"
    )
    parser.add_argument(
        "--dataset",
        default="synthetic",
        help="Dataset name: synthetic, MH_01_easy (EuRoC), dataset-room1_512_16 (TUM-VI), ...",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=None,
        help="Root folder containing euroc/ and tum_vi/ sequences",
    )
    parser.add_argument("--frames", type=int, default=60, help="Max frames to process")
    parser.add_argument("--drones", type=int, default=1, help="Number of cooperative drones")
    parser.add_argument(
        "--verify-alignment",
        action="store_true",
        help="Verify Python SRS constants match embedded mili_config.h",
    )
    args = parser.parse_args(argv)

    if args.verify_alignment:
        checks = verify_embedded_alignment()
        print("Embedded alignment checks:")
        for key, ok in checks.items():
            status = "OK" if ok else "FAIL"
            print(f"  {key}: {status}")
        if not all(checks.values()):
            return 1

    print("=" * 60)
    print("Mili VIO — Integrated Runtime")
    print(f"  Dataset: {args.dataset}  |  Frames: {args.frames}  |  Drones: {args.drones}")
    print("  Pipeline: Camera/IMU → BNN → Factor Graph → Sharing → FC")
    print("=" * 60)

    try:
        result = run_integrated(
            dataset_name=args.dataset,
            dataset_root=args.dataset_root,
            max_frames=args.frames,
            num_drones=args.drones,
        )
    except FileNotFoundError as exc:
        print(f"\nError: {exc}")
        print("\nTo use EuRoC/TUM-VI, download sequences under data/datasets/")
        print("  data/datasets/euroc/MH_01_easy/mav0/...")
        print("  data/datasets/tum_vi/dataset-room1_512_16/...")
        return 1

    if isinstance(result, list):
        for i, r in enumerate(result):
            _print_result(r, drone_id=i)
    else:
        _print_result(result)

    return 0


def _print_result(r, drone_id: int = 0) -> None:
    prefix = f"Drone {drone_id}: " if drone_id else ""
    print(f"\n{prefix}Results ({r.dataset_name})")
    print(f"  Frames processed:    {r.frames_processed} (skipped {r.frames_skipped})")
    print(f"  State update rate:   {r.state_update_hz:.1f} Hz (target 20 Hz)")
    print(f"  Mean position error: {r.mean_position_error_m:.3f} m")
    print(f"  Mean uncertainty:    {r.mean_uncertainty:.3f} m")
    print(f"  BNN extraction:      {r.mean_extraction_ms:.2f} ms")
    print(f"  FG optimization:     {r.mean_optimization_ms:.2f} ms")
    print(f"  Sharing events:      {r.sharing_events}")
    print(f"  Landmarks received:  {r.landmarks_received}")
    spec = "PASS" if r.meets_position_spec else "FAIL"
    print(f"  Position spec:       {spec} (< 0.5 m)")


if __name__ == "__main__":
    sys.exit(main())
