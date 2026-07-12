"""Tests for FR-2 SRS validation."""

from pathlib import Path

from mili_vio.factor_graph.srs_validation import validate_fr2_srs, validate_on_dataset
from mili_vio.vio.datasets.synthetic import generate_synthetic


def test_validate_on_synthetic_dataset() -> None:
    ds = generate_synthetic(num_frames=12, seed=7)
    report = validate_on_dataset(ds, scenario="open_field", keyframe_interval=5)
    assert report.frames == 12
    assert report.max_memory_bytes <= report.memory_budget_bytes
    assert report.meets_memory_spec
    assert report.backend in ("scipy_factor_graph", "gtsam")
    assert report.max_optimization_time_ms >= 0
    assert report.mean_orientation_error_deg >= 0


def test_fr2_srs_validation_runs(tmp_path: Path) -> None:
    report = validate_fr2_srs(max_frames=12, include_scenarios=True)
    assert len(report.reports) >= 4
    assert all(r.meets_memory_spec for r in report.reports)
    assert all("mean_orientation_error_deg" in r.__dict__ for r in report.reports)


def test_fr2_reports_loop_closure_metric() -> None:
    report = validate_fr2_srs(max_frames=12, include_scenarios=False)
    assert len(report.reports) == 1
    assert report.reports[0].loop_closures >= 0
