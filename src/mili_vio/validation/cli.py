"""CLI for Phase 6 SRS validation."""

from __future__ import annotations

import argparse
from pathlib import Path

from mili_vio.validation.datasets import check_datasets, download_all_datasets
from mili_vio.validation.orchestrator import run_phase6_validation, save_phase6_report
from mili_vio.validation.srs_evidence import (
    evaluate_srs_evidence,
    print_srs_evidence_table,
    save_srs_evidence,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 6 — unified SRS acceptance validation",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Fast CI mode (30 frames, drone sweep 2/4/12)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full validation (500 frames, drone sweep 2–12)",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download EuRoC/TUM-VI sequences before benchmarking",
    )
    parser.add_argument(
        "--check-datasets",
        action="store_true",
        help="Only check dataset presence and exit",
    )
    parser.add_argument(
        "--skip-embedded",
        action="store_true",
        help="Skip embedded C build/CTest (Python-only validation)",
    )
    parser.add_argument(
        "--transport",
        default="simulated",
        choices=["simulated", "udp"],
        help="FR-3 network transport",
    )
    parser.add_argument(
        "--evidence",
        action="store_true",
        help="Print SRS evidence matrix (proof level per metric)",
    )
    parser.add_argument(
        "--evidence-only",
        action="store_true",
        help="Only run SRS evidence matrix (no full Phase 6 suite)",
    )
    parser.add_argument(
        "--include-embedded",
        action="store_true",
        help="Include embedded host sim in evidence matrix (slow)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/benchmarks/phase6"),
        help="Report output directory",
    )
    args = parser.parse_args()

    if args.check_datasets:
        status = check_datasets()
        print(f"Dataset root: {status.root}")
        for ds in status.datasets:
            mark = "OK" if ds.present else "MISSING"
            gt = "GT" if ds.has_ground_truth else "no-GT"
            print(f"  [{mark}] {ds.kind}/{ds.name} ({gt})")
        if status.missing:
            print(f"\nMissing: {', '.join(status.missing)}")
            print("Run: python scripts/download_datasets.py --download")
        return

    if args.download:
        messages = download_all_datasets()
        for msg in messages:
            print(msg)

    quick = not args.full

    if args.evidence_only:
        matrix = evaluate_srs_evidence(
            quick=quick,
            include_embedded=args.include_embedded,
        )
        path = save_srs_evidence(matrix, args.output_dir)
        print_srs_evidence_table(matrix)
        print(f"\nEvidence report: {path}")
        print(f"Proven (real_data/hardware): {matrix.proven_count}/10")
        return

    print("=" * 60)
    print(f"Phase 6 SRS Validation ({'quick' if quick else 'full'})")
    print("=" * 60)

    report = run_phase6_validation(
        quick=quick,
        download=args.download,
        skip_embedded=args.skip_embedded,
        transport=args.transport,
        output_dir=args.output_dir,
    )
    path = save_phase6_report(report, args.output_dir)

    print(f"\nDatasets missing: {len(report.dataset_status.missing)}")
    print(f"FG vs EKF scenarios (synthetic): {'PASS' if report.fg_ekf_scenarios.all_pass else 'FAIL'}")
    real_n = len(report.fg_ekf_real.real_datasets)
    print(
        f"FG vs EKF real data ({real_n} seq): "
        f"{'PASS' if report.fg_ekf_real.all_pass else 'FAIL/N/A'}"
    )
    print(f"FR-1 SRS: {'PASS' if report.fr1_srs.get('all_pass') else 'FAIL'}")
    print(f"FR-2 SRS: {'PASS' if report.fr2_srs.get('all_pass') else 'FAIL'}")
    print(f"FR-3 drone sweep: {'PASS' if report.fr3_sweep.all_pass else 'FAIL'}")
    print(f"Embedded C: {'PASS' if report.embedded.all_pass else 'SKIP/FAIL'}")
    print(f"Field tests: manual (GPS-denied, fleet 2–12)")
    print(f"\nAutomated suite: {'ALL PASS' if report.automated_pass else 'SOME FAILED'}")
    print(f"SRS-grade real data: {'YES' if report.srs_grade_real_data else 'NO (download datasets)'}")
    print(f"\nReport: {path}")

    if args.evidence:
        matrix = evaluate_srs_evidence(
            quick=quick,
            include_embedded=not args.skip_embedded,
        )
        ev_path = save_srs_evidence(matrix, args.output_dir)
        print_srs_evidence_table(matrix)
        print(f"Evidence report: {ev_path}")


if __name__ == "__main__":
    main()
