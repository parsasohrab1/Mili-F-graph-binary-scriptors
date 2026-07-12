"""CLI for VIO benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

from mili_vio.benchmark.dashboard import generate_dashboard
from mili_vio.benchmark.runner import run_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="Run VIO benchmark: Factor-Graph vs EKF")
    parser.add_argument("--dataset", default="synthetic", help="Dataset name (synthetic, MH_01_easy, ...)")
    parser.add_argument("--dataset-root", type=Path, default=None, help="Root path for EuRoC/TUM-VI")
    parser.add_argument("--max-frames", type=int, default=None, help="Max frames to process")
    parser.add_argument("--output-dir", type=Path, default=Path("data/benchmarks"), help="Output directory")
    args = parser.parse_args()

    print("=" * 60)
    print("Phase 1 — VIO Benchmark (Factor-Graph vs EKF)")
    print("=" * 60)

    comparison = run_benchmark(
        dataset_name=args.dataset,
        dataset_root=args.dataset_root,
        max_frames=args.max_frames,
        output_dir=args.output_dir,
    )

    dashboard_path = args.output_dir / f"dashboard_{comparison.dataset_name}.png"
    generate_dashboard(comparison, dashboard_path)

    print(f"\nDataset: {comparison.dataset_name} ({comparison.scenario})")
    print(f"Backend: {comparison.backend}")
    print("\n--- Factor Graph ---")
    fg = comparison.factor_graph
    print(f"  Position error: {fg.position_error_m:.4f} m")
    print(f"  ATE RMSE:       {fg.ate_rmse_m:.4f} m")
    print(f"  Optimization:   {fg.optimization_time_ms:.2f} ms")
    print(f"  Repeatability:  {fg.repeatability_mean:.2%}")
    print(f"  Loop closures:  {fg.loop_closures}")

    print("\n--- EKF Baseline ---")
    ekf = comparison.ekf
    print(f"  Position error: {ekf.position_error_m:.4f} m")
    print(f"  ATE RMSE:       {ekf.ate_rmse_m:.4f} m")

    print(f"\nImprovement over EKF: {comparison.improvement_pct:.1f}%")
    print(f"Position spec (<0.5m): {'PASS' if comparison.meets_position_spec else 'FAIL'}")
    print(f"Improvement spec (>=30%): {'PASS' if comparison.meets_improvement_spec else 'FAIL'}")
    print(f"\nDashboard saved: {dashboard_path}")


if __name__ == "__main__":
    main()
