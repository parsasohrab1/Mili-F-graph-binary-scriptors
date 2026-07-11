"""Tests for FR-2 scenario runner."""

from pathlib import Path

from mili_vio.factor_graph.scenario_runner import run_scenario_benchmark


def test_scenario_benchmark_runs(tmp_path: Path) -> None:
    report = run_scenario_benchmark(tmp_path, frames_per_scenario=15)
    assert "scenarios" in report
    assert len(report["scenarios"]) == 4
    for scenario in ["urban_canyon", "forest_dense", "indoor_complex", "open_field"]:
        assert scenario in report["scenarios"]
        m = report["scenarios"][scenario]
        assert "mean_position_error_m" in m
        assert "loop_closures" in m
