"""CLI for FR-2 scenario benchmark and SRS validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mili_vio.factor_graph.scenario_runner import run_scenario_benchmark
from mili_vio.factor_graph.srs_validation import save_fr2_srs_report, validate_fr2_srs
from mili_vio.vio.backend.gtsam_backend import GTSAM_AVAILABLE


def main() -> None:
    parser = argparse.ArgumentParser(description="FR-2 factor-graph scenario benchmark")
    parser.add_argument("--frames", type=int, default=60, help="Frames per scenario")
    parser.add_argument("--output-dir", type=Path, default=Path("data/benchmarks/fr2"))
    parser.add_argument(
        "--validate-srs",
        action="store_true",
        help="Run full SRS validation (position, orientation, time, loop, memory)",
    )
    parser.add_argument(
        "--dataset",
        default="synthetic",
        help="Dataset for real-data validation: synthetic, MH_01_easy, ...",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("data/datasets"),
        help="Root for EuRoC/TUM-VI sequences",
    )
    parser.add_argument(
        "--scenarios-only",
        action="store_true",
        help="Run only 4 SRS synthetic scenarios (skip real dataset)",
    )
    args = parser.parse_args()

    if args.validate_srs:
        _run_srs_validation(args)
        return

    print("=" * 60)
    print("FR-2 Scenario Benchmark (4 SRS scenarios)")
    print(f"  Backend: {'GTSAM' if GTSAM_AVAILABLE else 'SciPy factor-graph'}")
    print("=" * 60)

    report = run_scenario_benchmark(args.output_dir, args.frames)

    for scenario, metrics in report["scenarios"].items():
        print(f"\n--- {scenario} ---")
        print(
            f"  Position error:    {metrics['mean_position_error_m']:.4f} m  "
            f"{'PASS' if metrics['meets_position_spec'] else 'FAIL'}"
        )
        print(
            f"  Orientation error: {metrics['mean_orientation_error_deg']:.4f} deg  "
            f"{'PASS' if metrics['meets_orientation_spec'] else 'FAIL'}"
        )
        print(
            f"  Optimization:      {metrics['max_optimization_time_ms']:.2f} ms (max)  "
            f"{'PASS' if metrics['meets_optimization_spec'] else 'FAIL'}"
        )
        print(
            f"  Loop closures:     {metrics['loop_closures']}  "
            f"{'PASS' if metrics['meets_loop_closure_spec'] else 'FAIL'}"
        )
        print(f"  Memory budget:     {'PASS' if metrics['memory_within_budget'] else 'FAIL'}")

    print(f"\nOverall: {'ALL PASS' if report['all_scenarios_pass'] else 'SOME FAILED'}")


def _run_srs_validation(args) -> None:
    print("=" * 60)
    print("FR-2 SRS Validation")
    print(f"  Backend: {'GTSAM' if GTSAM_AVAILABLE else 'SciPy factor-graph'}")
    print(f"  Targets: pos < 0.5 m | orient < 2 deg | opt < 5 ms | mem <= 2 MB")
    print("=" * 60)

    report = validate_fr2_srs(
        dataset_name=args.dataset,
        dataset_root=args.dataset_root,
        max_frames=args.frames,
        include_scenarios=True,
        euroc_sequence=None if args.scenarios_only else args.dataset,
    )
    path = save_fr2_srs_report(report, args.output_dir)

    for r in report.reports:
        print(f"\n--- {r.dataset} / {r.scenario} ---")
        print(f"  Position:     {r.mean_position_error_m:.4f} m  {'PASS' if r.meets_position_spec else 'FAIL'}")
        print(f"  Orientation:  {r.mean_orientation_error_deg:.4f} deg  {'PASS' if r.meets_orientation_spec else 'FAIL'}")
        print(f"  Opt (max):    {r.max_optimization_time_ms:.2f} ms  {'PASS' if r.meets_optimization_spec else 'FAIL'}")
        print(f"  Loop closure: {r.loop_closures}  {'PASS' if r.meets_loop_closure_spec else 'FAIL'}")
        print(f"  Memory:       {r.max_memory_bytes} / {r.memory_budget_bytes} B  {'PASS' if r.meets_memory_spec else 'FAIL'}")
        print(f"  Backend:      {r.backend}")

    for note in report.notes:
        print(f"\nNote: {note}")

    print(f"\nReport: {path}")
    print(f"Overall: {'ALL PASS' if report.all_pass else 'SOME FAILED'}")
    if not report.all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
