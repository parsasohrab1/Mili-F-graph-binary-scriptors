"""Benchmark metrics for VIO evaluation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from mili_vio.vio.backend.scipy_backend import PoseNode
from mili_vio.vio.datasets.base import GroundTruthPose, VIODataset


@dataclass
class TrajectoryMetrics:
    ate_rmse_m: float
    ate_mean_m: float
    ate_max_m: float
    position_error_m: float
    optimization_time_ms: float
    repeatability_mean: float
    num_poses: int
    loop_closures: int


@dataclass
class BenchmarkComparison:
    dataset_name: str
    scenario: str
    factor_graph: TrajectoryMetrics
    ekf: TrajectoryMetrics
    improvement_pct: float
    meets_position_spec: bool
    meets_improvement_spec: bool
    backend: str


def _align_trajectories(
    estimated: list[PoseNode],
    ground_truth: list[GroundTruthPose],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    if not estimated or not ground_truth:
        return np.zeros((0, 3)), np.zeros((0, 3))

    est_positions = np.array([p.position for p in estimated])
    gt_times = np.array([g.timestamp_ns for g in ground_truth])
    gt_positions = np.array([g.position for g in ground_truth])

    matched_gt = []
    for pose in estimated:
        idx = int(np.argmin(np.abs(gt_times - pose.timestamp_ns)))
        matched_gt.append(gt_positions[idx])
    matched_gt_arr = np.array(matched_gt)

    # Sim(3) alignment via centroid + scale (simplified Umeyama)
    est_centroid = est_positions.mean(axis=0)
    gt_centroid = matched_gt_arr.mean(axis=0)
    est_centered = est_positions - est_centroid
    gt_centered = matched_gt_arr - gt_centroid

    scale = np.linalg.norm(gt_centered) / (np.linalg.norm(est_centered) + 1e-9)
    est_aligned = est_centered * scale + gt_centroid
    return est_aligned, matched_gt_arr


def compute_trajectory_metrics(
    poses: list[PoseNode],
    dataset: VIODataset,
    optimization_time_ms: float = 0.0,
    repeatability_scores: list[float] | None = None,
    loop_closures: int = 0,
) -> TrajectoryMetrics:
    if not poses:
        return TrajectoryMetrics(0, 0, 0, 0, optimization_time_ms, 0, 0, loop_closures)

    if dataset.ground_truth:
        est_aligned, gt = _align_trajectories(poses, dataset.ground_truth)
        errors = np.linalg.norm(est_aligned - gt, axis=1)
    else:
        errors = np.array([np.linalg.norm(p.position) for p in poses])

    rep = float(np.mean(repeatability_scores)) if repeatability_scores else 0.0
    return TrajectoryMetrics(
        ate_rmse_m=float(np.sqrt(np.mean(errors ** 2))),
        ate_mean_m=float(np.mean(errors)),
        ate_max_m=float(np.max(errors)),
        position_error_m=float(np.mean(errors)),
        optimization_time_ms=optimization_time_ms,
        repeatability_mean=rep,
        num_poses=len(poses),
        loop_closures=loop_closures,
    )


def compare_methods(
    dataset: VIODataset,
    fg_poses: list[PoseNode],
    ekf_poses: list[PoseNode],
    fg_opt_time_ms: float,
    ekf_time_ms: float,
    repeatability: list[float],
    loop_closures: int,
    backend: str,
    acceptance_error_m: float = 1.0,
    acceptance_improvement_pct: float = 30.0,
) -> BenchmarkComparison:
    fg_metrics = compute_trajectory_metrics(
        fg_poses, dataset, fg_opt_time_ms, repeatability, loop_closures
    )
    ekf_metrics = compute_trajectory_metrics(ekf_poses, dataset, ekf_time_ms)

    if ekf_metrics.position_error_m > 0:
        improvement = (
            (ekf_metrics.position_error_m - fg_metrics.position_error_m)
            / ekf_metrics.position_error_m
            * 100
        )
    else:
        improvement = 0.0

    scenario = dataset.dataset_type.value
    return BenchmarkComparison(
        dataset_name=dataset.name,
        scenario=scenario,
        factor_graph=fg_metrics,
        ekf=ekf_metrics,
        improvement_pct=float(improvement),
        meets_position_spec=fg_metrics.position_error_m < acceptance_error_m,
        meets_improvement_spec=improvement >= acceptance_improvement_pct,
        backend=backend,
    )
