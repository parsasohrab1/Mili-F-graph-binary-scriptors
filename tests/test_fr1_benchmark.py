"""Tests for FR-1 benchmark."""

from pathlib import Path

from mili_vio.descriptors.benchmark import run_fr1_benchmark


def test_fr1_benchmark_bnn(tmp_path: Path) -> None:
    report = run_fr1_benchmark(tmp_path, num_frames=5)
    assert "metrics" in report
    assert "mean_time_ms" in report["metrics"]
    assert report["source"] == "bnn"


def test_fr1_benchmark_fallback(tmp_path: Path) -> None:
    report = run_fr1_benchmark(tmp_path, num_frames=5, force_fallback=True)
    assert report["source"] == "fallback"
