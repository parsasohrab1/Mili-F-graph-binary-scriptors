"""CLI for FR-3 cooperative sharing benchmark and SRS validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mili_vio.sharing.benchmark import run_fr3_benchmark
from mili_vio.sharing.srs_validation import save_fr3_srs_report, validate_12_drone_group, validate_fr3_srs


def main() -> None:
    parser = argparse.ArgumentParser(description="FR-3 cooperative sharing benchmark")
    parser.add_argument("--drones", type=int, default=6, help="Number of drones (max 12)")
    parser.add_argument("--steps", type=int, default=100, help="Simulation steps")
    parser.add_argument("--output-dir", type=Path, default=Path("data/benchmarks/fr3"))
    parser.add_argument(
        "--validate-srs",
        action="store_true",
        help="Run SRS acceptance validation",
    )
    parser.add_argument(
        "--transport",
        choices=["simulated", "udp", "multicast", "uwb", "wifi"],
        default="simulated",
        help="Network transport: simulated or real UDP",
    )
    parser.add_argument("--host", default="127.0.0.1", help="UDP bind host")
    parser.add_argument(
        "--12-drones",
        action="store_true",
        dest="twelve_drones",
        help="Validate max SRS group size (12 drones)",
    )
    args = parser.parse_args()

    if args.validate_srs:
        _run_srs_validation(args)
        return

    print("=" * 60)
    print("FR-3 Benchmark — Event-Driven Cooperative Sharing")
    print(f"  Transport: {args.transport}")
    print("=" * 60)

    report = run_fr3_benchmark(args.drones, args.steps, args.output_dir, transport=args.transport)
    m = report["metrics"]

    print(f"\nDrones: {report['num_drones']}  Steps: {report['steps']}")
    print(f"Transport:           {report.get('transport', 'simulated')}")
    print(f"Events triggered:    {m['events_triggered']}")
    print(f"Landmarks received:  {m['landmarks_received']}")
    print(
        f"\nBandwidth reduction: {m['bandwidth_reduction_pct']:.1f}%  "
        f"{'PASS' if m['meets_bandwidth_spec'] else 'FAIL'}"
    )
    print(
        f"Accuracy improvement:{m['accuracy_improvement_pct']:.1f}%  "
        f"{'PASS' if m['meets_accuracy_spec'] else 'FAIL'}"
    )
    print(
        f"Sharing latency:     {m['mean_sharing_latency_ms']:.2f} ms  "
        f"{'PASS' if m['meets_latency_spec'] else 'FAIL'}"
    )
    print(f"Network latency:     {m['max_network_latency_ms']:.2f} ms (max)")
    print(f"\nOverall: {'ALL PASS' if report['all_pass'] else 'SOME FAILED'}")


def _run_srs_validation(args) -> None:
    print("=" * 60)
    print("FR-3 SRS Validation")
    print(f"  Targets: bandwidth >= 70% | accuracy >= 40% | latency < 20 ms")
    print(f"  Transport: {args.transport}")
    print("=" * 60)

    if args.twelve_drones:
        report = validate_12_drone_group(steps=args.steps, transport=args.transport)
    else:
        report = validate_fr3_srs(
            num_drones=args.drones,
            steps=args.steps,
            transport=args.transport,
            host=args.host,
        )

    path = save_fr3_srs_report(report, args.output_dir)
    print(f"\nDrones: {report.num_drones}  Steps: {report.steps}")
    print(f"Hardware transport:  {report.is_hardware}")
    print(
        f"Bandwidth reduction: {report.bandwidth_reduction_pct:.1f}%  "
        f"{'PASS' if report.meets_bandwidth_spec else 'FAIL'}"
    )
    print(
        f"Accuracy improvement:{report.accuracy_improvement_pct:.1f}%  "
        f"{'PASS' if report.meets_accuracy_spec else 'FAIL'}"
    )
    print(
        f"Sharing latency:     {report.mean_sharing_latency_ms:.2f} ms  "
        f"{'PASS' if report.meets_latency_spec else 'FAIL'}"
    )
    print(f"Network latency:     {report.max_network_latency_ms:.2f} ms (max)")
    print(f"Events: {report.events_triggered}  Received: {report.landmarks_received}")
    for note in report.notes:
        print(f"Note: {note}")
    print(f"\nReport: {path}")
    print(f"Overall: {'ALL PASS' if report.all_pass else 'SOME FAILED'}")
    if not report.all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
