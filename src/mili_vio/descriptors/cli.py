"""CLI for FR-1 BNN descriptor benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

from mili_vio.descriptors.benchmark import run_fr1_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="FR-1 BNN descriptor benchmark")
    parser.add_argument("--frames", type=int, default=10, help="Frames in test sequence")
    parser.add_argument("--fallback", action="store_true", help="Force ORB/BRIEF fallback")
    parser.add_argument("--output-dir", type=Path, default=Path("data/benchmarks/fr1"))
    args = parser.parse_args()

    print("=" * 60)
    print("FR-1 Benchmark — BNN Binary Descriptor Extraction")
    print("=" * 60)

    report = run_fr1_benchmark(args.output_dir, args.frames, args.fallback)
    m = report["metrics"]

    print(f"\nSource: {report['source']}")
    print(f"Mean extraction time:  {m['mean_time_ms']:.3f} ms (max {m['max_time_ms']:.3f} ms)  {'PASS' if m['meets_time_spec'] else 'FAIL'}")
    print(f"Mean repeatability:    {m['mean_repeatability']*100:.1f}%  {'PASS' if m['meets_repeatability_spec'] else 'FAIL'}")
    print(f"Mean energy:           {m['mean_energy_mj']:.3f} mJ  {'PASS' if m['meets_energy_spec'] else 'FAIL'}")
    print(f"\nOverall: {'ALL PASS' if report['all_pass'] else 'SOME FAILED'}")


if __name__ == "__main__":
    main()
