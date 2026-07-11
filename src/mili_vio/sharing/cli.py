"""CLI for FR-3 cooperative sharing benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

from mili_vio.sharing.benchmark import run_fr3_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="FR-3 cooperative sharing benchmark")
    parser.add_argument("--drones", type=int, default=6, help="Number of drones (max 12)")
    parser.add_argument("--steps", type=int, default=100, help="Simulation steps")
    parser.add_argument("--output-dir", type=Path, default=Path("data/benchmarks/fr3"))
    args = parser.parse_args()

    print("=" * 60)
    print("FR-3 Benchmark — Event-Driven Cooperative Sharing")
    print("=" * 60)

    report = run_fr3_benchmark(args.drones, args.steps, args.output_dir)
    m = report["metrics"]

    print(f"\nDrones: {report['num_drones']}  Steps: {report['steps']}")
    print(f"Events triggered:    {m['events_triggered']}")
    print(f"Landmarks received:  {m['landmarks_received']}")
    print(f"\nBandwidth reduction: {m['bandwidth_reduction_pct']:.1f}%  {'PASS' if m['meets_bandwidth_spec'] else 'FAIL'}")
    print(f"Accuracy improvement:{m['accuracy_improvement_pct']:.1f}%  {'PASS' if m['meets_accuracy_spec'] else 'FAIL'}")
    print(f"Sharing latency:     {m['mean_sharing_latency_ms']:.2f} ms  {'PASS' if m['meets_latency_spec'] else 'FAIL'}")
    print(f"Network latency:     {m['max_network_latency_ms']:.2f} ms (max)")
    print(f"\nOverall: {'ALL PASS' if report['all_pass'] else 'SOME FAILED'}")


if __name__ == "__main__":
    main()
