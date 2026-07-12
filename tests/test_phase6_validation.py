"""Phase 6 validation tests (quick / synthetic for CI)."""

from __future__ import annotations

import pytest

from mili_vio.validation.datasets import check_datasets
from mili_vio.validation.drone_sweep import validate_drone_group_sweep
from mili_vio.validation.orchestrator import run_phase6_validation
from mili_vio.validation.scenario_matrix import run_fg_ekf_scenario_matrix


def test_dataset_check_runs() -> None:
    status = check_datasets()
    assert status.root.name == "datasets" or "datasets" in str(status.root)


def test_fg_ekf_scenario_matrix_quick() -> None:
    report = run_fg_ekf_scenario_matrix(max_frames=8)
    assert len(report.scenarios) == 4
    for row in report.scenarios:
        assert "dataset_name" in row
        assert "improvement_pct" in row


def test_drone_sweep_small() -> None:
    report = validate_drone_group_sweep(drone_counts=[2, 4], steps=20)
    assert len(report.reports) == 2
    assert report.drone_counts == [2, 4]


@pytest.fixture(scope="module")
def phase6_quick_report(tmp_path_factory: pytest.TempPathFactory):
    """Single quick validation run shared across tests (avoids duplicate OpenCV load)."""
    out = tmp_path_factory.mktemp("phase6")
    report = run_phase6_validation(
        quick=True, skip_embedded=True, output_dir=out, max_frames=8,
    )
    return report, out


def test_phase6_quick_skip_embedded(phase6_quick_report) -> None:
    report, _ = phase6_quick_report
    assert report.mode == "quick"
    assert len(report.fg_ekf_scenarios.scenarios) == 4
    assert report.fr2_srs.get("reports")
    assert report.field_tests["gps_denied_flight"]["status"] == "manual"


def test_phase6_report_file_written(phase6_quick_report) -> None:
    report, out = phase6_quick_report
    path = out / "phase6_validation_report.yaml"
    assert path.exists()
    assert report.timestamp
