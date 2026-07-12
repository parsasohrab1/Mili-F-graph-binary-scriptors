"""CLI for FR-1 BNN descriptor benchmark and SRS hardware validation."""

from __future__ import annotations

import argparse
from pathlib import Path

from mili_vio.descriptors.benchmark import run_fr1_benchmark
from mili_vio.descriptors.bnn.hw_validation import save_srs_report, validate_bnn_srs


def main() -> None:
    parser = argparse.ArgumentParser(description="FR-1 BNN descriptor benchmark")
    parser.add_argument("--frames", type=int, default=10, help="Frames in test sequence")
    parser.add_argument("--fallback", action="store_true", help="Force ORB/BRIEF fallback")
    parser.add_argument("--output-dir", type=Path, default=Path("data/benchmarks/fr1"))
    parser.add_argument(
        "--validate-srs",
        action="store_true",
        help="Run SRS acceptance validation (time, repeatability, energy)",
    )
    parser.add_argument(
        "--transport",
        choices=["simulated", "loopback", "spidev", "serial"],
        default=None,
        help="BNN transport to Product 1 chip",
    )
    parser.add_argument(
        "--serial-port",
        default="",
        help="Serial port for USB BNN bridge (e.g. COM3, /dev/ttyUSB0)",
    )
    parser.add_argument(
        "--ping",
        action="store_true",
        help="Ping BNN hardware and print firmware version",
    )
    args = parser.parse_args()

    if args.ping or args.validate_srs:
        _run_hardware_mode(args)
        return

    print("=" * 60)
    print("FR-1 Benchmark — BNN Binary Descriptor Extraction")
    print("=" * 60)

    report = run_fr1_benchmark(args.output_dir, args.frames, args.fallback)
    m = report["metrics"]

    print(f"\nSource: {report['source']}")
    print(
        f"Mean extraction time:  {m['mean_time_ms']:.3f} ms "
        f"(max {m['max_time_ms']:.3f} ms)  {'PASS' if m['meets_time_spec'] else 'FAIL'}"
    )
    print(
        f"Mean repeatability:    {m['mean_repeatability']*100:.1f}%  "
        f"{'PASS' if m['meets_repeatability_spec'] else 'FAIL'}"
    )
    print(
        f"Mean energy:           {m['mean_energy_mj']:.3f} mJ  "
        f"{'PASS' if m['meets_energy_spec'] else 'FAIL'}"
    )
    print(f"\nOverall: {'ALL PASS' if report['all_pass'] else 'SOME FAILED'}")


def _run_hardware_mode(args) -> None:
    from mili_vio.descriptors.bnn.driver import create_bnn_driver
    from mili_vio.descriptors.bnn.api import load_phase3_config

    cfg = load_phase3_config()
    if args.transport:
        cfg.setdefault("phase3", {}).setdefault("bnn", {})["transport"] = args.transport
    if args.serial_port:
        cfg["phase3"]["bnn"]["serial_port"] = args.serial_port

    driver = create_bnn_driver(cfg)

    print("=" * 60)
    print("FR-1 — BNN Product 1 Hardware Interface")
    print(f"  Transport: {cfg['phase3']['bnn'].get('transport')}")
    print(f"  Hardware:  {getattr(driver, 'is_hardware', False)}")
    print("=" * 60)

    if args.ping:
        try:
            v = driver.get_version()
            print(f"BNN firmware version: {v[0]}.{v[1]}.{v[2]}")
        except Exception as exc:
            print(f"Ping failed: {exc}")
            raise SystemExit(1) from exc

    if args.validate_srs:
        report = validate_bnn_srs(
            config=cfg,
            num_frames=max(args.frames, 20),
            transport=args.transport,
            serial_port=args.serial_port,
        )
        path = save_srs_report(report, args.output_dir)
        print(f"\nSRS Validation ({report.frames_tested} frames)")
        print(f"  Chip time (max):     {report.max_chip_time_ms:.3f} ms  {'PASS' if report.meets_time_spec else 'FAIL'}")
        print(f"  Repeatability:       {report.mean_repeatability_pct:.1f}%  {'PASS' if report.meets_repeatability_spec else 'FAIL'}")
        print(f"  Energy (max):        {report.max_energy_mj:.3f} mJ  {'PASS' if report.meets_energy_spec else 'FAIL'}")
        print(f"  Hardware connected:  {report.hardware_connected}")
        for note in report.notes:
            print(f"  Note: {note}")
        print(f"\nReport saved: {path}")
        print(f"Overall: {'ALL PASS' if report.all_pass else 'SOME FAILED'}")
        if not report.all_pass:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
