"""Tests for FR-2 sliding-window factor graph."""

import numpy as np

from mili_vio.factor_graph.covariance import uncertainty_metric
from mili_vio.factor_graph.estimator import FR2FactorGraphEstimator
from mili_vio.factor_graph.optimizer import (
    FastFactorGraphOptimizer,
    IMUFactorData,
    VisualFactorData,
)
from mili_vio.factor_graph.sliding_window import SlidingWindowFactorGraph
from mili_vio.vio.datasets.base import CameraIntrinsics
from mili_vio.vio.datasets.synthetic import generate_synthetic
from mili_vio.vio.backend.pose_utils import pose_to_vector
from mili_vio.vio.imu_preintegration import IMUPreintegrator


def test_sliding_window_adds_nodes() -> None:
    intrinsics = CameraIntrinsics(fx=500, fy=500, cx=320, cy=240)
    graph = SlidingWindowFactorGraph(intrinsics=intrinsics, max_poses=5, max_landmarks=20)
    graph.add_pose(1000, np.zeros(3), np.eye(3), fixed=True)
    idx = graph.add_pose(2000, np.array([0.1, 0, 0]), np.eye(3))
    graph.add_visual_observation(0, np.array([320.0, 240.0]))
    graph.add_visual_observation(1, np.array([325.0, 240.0]))
    assert len(graph.state.poses) == 2
    assert len(graph.state.landmarks) >= 1


def test_optimizer_runs_under_time_budget() -> None:
    intrinsics = CameraIntrinsics(fx=500, fy=500, cx=320, cy=240)
    opt = FastFactorGraphOptimizer(max_time_ms=5.0, max_iterations=3)
    poses = [pose_to_vector(np.array([i * 0.1, 0, 0]), np.eye(3)) for i in range(3)]
    landmarks = [np.array([1.0, 0.5, 3.0])]
    imu = [IMUFactorData(0, 1, np.array([0.1, 0, 0]), np.eye(3)), IMUFactorData(1, 2, np.array([0.1, 0, 0]), np.eye(3))]
    visual = [VisualFactorData(1, 0, np.array([320.0, 240.0])), VisualFactorData(2, 0, np.array([315.0, 240.0]))]
    report = opt.optimize(poses, landmarks, imu, visual, [], intrinsics)
    assert report.optimization_time_ms < 500.0
    assert len(report.pose_states) == 3


def test_memory_within_budget() -> None:
    intrinsics = CameraIntrinsics(fx=500, fy=500, cx=320, cy=240)
    graph = SlidingWindowFactorGraph(
        intrinsics=intrinsics,
        max_poses=12,
        memory_budget_bytes=2 * 1024 * 1024,
    )
    for i in range(20):
        graph.add_pose(i * 1000, np.array([i * 0.05, 0, 0]), np.eye(3))
    mem = graph.memory_usage()
    assert mem.within_budget
    assert mem.used_bytes <= 2 * 1024 * 1024


def test_fr2_estimator_on_synthetic() -> None:
    dataset = generate_synthetic(num_frames=20, seed=99)
    estimator = FR2FactorGraphEstimator()
    result = estimator.run_on_dataset(dataset, scenario="open_field", keyframe_interval=5)
    assert len(result.estimates) > 0
    assert result.mean_optimization_time_ms >= 0
    assert result.memory_within_budget


def test_uncertainty_metric_positive() -> None:
    cov = np.diag([0.01, 0.02, 0.03, 0.001, 0.001, 0.001])
    unc = uncertainty_metric(cov)
    assert unc > 0


def test_covariance_from_factors() -> None:
    from mili_vio.factor_graph.covariance import estimate_pose_covariance

    intrinsics = CameraIntrinsics(fx=500, fy=500, cx=320, cy=240)
    poses = [np.zeros(6), np.array([0.2, 0, 0, 0, 0, 0])]
    landmarks = [np.array([1.0, 0.0, 3.0])]
    imu = [IMUFactorData(0, 1, np.array([0.2, 0, 0]), np.eye(3))]
    visual = [VisualFactorData(0, 0, np.array([320.0, 240.0])), VisualFactorData(1, 0, np.array([310.0, 240.0]))]
    cov = estimate_pose_covariance(poses, landmarks, imu, visual, [], intrinsics)
    assert cov.shape == (6, 6)
    assert cov[0, 0] > 0
