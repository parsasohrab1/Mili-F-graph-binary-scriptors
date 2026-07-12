"""Multi-drone cooperative validation sweep (2–12 drones)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from mili_vio.sharing.srs_validation import FR3SRSReport, validate_fr3_srs
from mili_vio.validation.config import phase6_section


@dataclass
class DroneSweepReport:
    reports: list[FR3SRSReport]
    drone_counts: list[int]
    all_pass: bool
    notes: list[str]


def validate_drone_group_sweep(
    drone_counts: Optional[list[int]] = None,
    steps: int = 80,
    transport: str = "simulated",
    config: Optional[dict] = None,
) -> DroneSweepReport:
    """Validate FR-3 SRS at each drone count in ``drone_counts``."""
    p6 = phase6_section(config)
    counts = drone_counts or p6.get("full", {}).get("drone_sweep", [2, 4, 6, 8, 10, 12])
    notes: list[str] = []
    reports: list[FR3SRSReport] = []

    for n in counts:
        report = validate_fr3_srs(num_drones=n, steps=steps, transport=transport)
        reports.append(report)
        if not report.all_pass:
            notes.append(f"{n} drones: FAILED bandwidth/accuracy/latency SRS")

    all_pass = all(r.all_pass for r in reports) if reports else False
    if all_pass:
        notes.append(f"All drone counts {counts} passed FR-3 SRS (simulated transport)")

    return DroneSweepReport(
        reports=reports,
        drone_counts=counts,
        all_pass=all_pass,
        notes=notes,
    )


def drone_sweep_to_dict(report: DroneSweepReport) -> dict:
    return {
        "drone_counts": report.drone_counts,
        "all_pass": report.all_pass,
        "notes": report.notes,
        "reports": [asdict(r) for r in report.reports],
    }
