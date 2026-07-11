"""Tests for benchmark metrics and runner."""

from pathlib import Path

import numpy as np

from mili_vio.benchmark.dashboard import generate_dashboard
from mili_vio.benchmark.metrics import compare_methods, compute_trajectory_metrics
from mili_vio.benchmark.runner import run_benchmark
from mili_vio.vio.backend.scipy_backend import PoseNode
from mili_vio.vio.datasets.synthetic import generate_synthetic


def test_compute_trajectory_metrics() -> None:
    dataset = generate_synthetic(num_frames=10, seed=1)
    poses = [
        PoseNode(i, dataset.ground_truth[i].timestamp_ns, dataset.ground_truth[i].position.copy(), np.eye(3))
        for i in range(len(dataset.ground_truth))
    ]
    metrics = compute_trajectory_metrics(poses, dataset, optimization_time_ms=5.0)
    assert metrics.position_error_m < 0.5
    assert metrics.num_poses == len(poses)


def test_run_benchmark_synthetic(tmp_path: Path) -> None:
    comparison = run_benchmark(
        dataset_name="synthetic",
        max_frames=30,
        output_dir=tmp_path,
    )
    assert comparison.dataset_name == "synthetic"
    assert comparison.factor_graph.num_poses > 0
    assert comparison.improvement_pct != 0 or comparison.ekf.position_error_m >= 0

    dashboard = generate_dashboard(comparison, tmp_path / "dashboard.png")
    assert dashboard.exists()
