"""CLI for FR-2 scenario benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

from mili_vio.factor_graph.scenario_runner import run_scenario_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="FR-2 factor-graph scenario benchmark")
    parser.add_argument("--frames", type=int, default=60, help="Frames per scenario")
    parser.add_argument("--output-dir", type=Path, default=Path("data/benchmarks/fr2"))
    args = parser.parse_args()

    print("=" * 60)
    print("FR-2 Scenario Benchmark (4 SRS scenarios)")
    print("=" * 60)

    report = run_scenario_benchmark(args.output_dir, args.frames)

    for scenario, metrics in report["scenarios"].items():
        print(f"\n--- {scenario} ---")
        print(f"  Position error:    {metrics['mean_position_error_m']:.4f} m  {'PASS' if metrics['meets_position_spec'] else 'FAIL'}")
        print(f"  Orientation error: {metrics['mean_orientation_error_deg']:.4f} deg  {'PASS' if metrics['meets_orientation_spec'] else 'FAIL'}")
        print(f"  Optimization:      {metrics['max_optimization_time_ms']:.2f} ms (max)  {'PASS' if metrics['meets_optimization_spec'] else 'FAIL'}")
        print(f"  Loop closures:     {metrics['loop_closures']}  {'PASS' if metrics['meets_loop_closure_spec'] else 'FAIL'}")
        print(f"  Memory budget:     {'PASS' if metrics['memory_within_budget'] else 'FAIL'}")

    print(f"\nOverall: {'ALL PASS' if report['all_scenarios_pass'] else 'SOME FAILED'}")


if __name__ == "__main__":
    main()
