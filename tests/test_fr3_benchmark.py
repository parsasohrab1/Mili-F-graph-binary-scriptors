"""Tests for FR-3 benchmark."""

from pathlib import Path

from mili_vio.sharing.benchmark import run_fr3_benchmark


def test_fr3_benchmark_runs(tmp_path: Path) -> None:
    report = run_fr3_benchmark(num_drones=4, steps=30, output_dir=tmp_path)
    assert "metrics" in report
    m = report["metrics"]
    assert "bandwidth_reduction_pct" in m
    assert "accuracy_improvement_pct" in m
