"""Offline VIO pipeline: camera + IMU + factor graph."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from mili_vio.vio.backend.ekf_baseline import VisualInertialEKF
from mili_vio.vio.backend.gtsam_backend import create_factor_graph
from mili_vio.vio.backend.scipy_backend import OptimizationResult, estimate_visual_odometry
from mili_vio.vio.datasets import load_phase1_config
from mili_vio.vio.datasets.base import VIODataset
from mili_vio.vio.frontend.visual import VisualFrontend
from mili_vio.vio.imu_preintegration import IMUPreintegrator
from mili_vio.vio.loop_closure import KeyframeObservation, LoopClosureDetector


@dataclass
class PipelineConfig:
    keyframe_interval: int = 5
    min_matches: int = 20
    loop_closure_enabled: bool = True
    min_keyframe_gap: int = 30
    hamming_threshold: int = 50
    min_loop_matches: int = 15


@dataclass
class FrameResult:
    frame_id: int
    timestamp_ns: int
    num_features: int
    num_matches: int
    is_keyframe: bool


@dataclass
class VIOPipelineResult:
    factor_graph_poses: list
    ekf_poses: list
    frame_results: list[FrameResult] = field(default_factory=list)
    optimization_results: list[OptimizationResult] = field(default_factory=list)
    loop_closures: int = 0
    repeatability_scores: list[float] = field(default_factory=list)
    total_time_ms: float = 0.0
    backend_used: str = "scipy_factor_graph"


class OfflineVIOPipeline:
    """Complete offline VIO pipeline with factor graph and EKF baseline."""

    def __init__(
        self,
        dataset: VIODataset,
        config: PipelineConfig | None = None,
        descriptor_type: str = "orb",
    ) -> None:
        self.dataset = dataset
        self.config = config or PipelineConfig()
        self.frontend = VisualFrontend(descriptor_type=descriptor_type, hamming_threshold=self.config.hamming_threshold)
        self.preintegrator = IMUPreintegrator()
        self.loop_detector = LoopClosureDetector(
            min_keyframe_gap=self.config.min_keyframe_gap,
            hamming_threshold=self.config.hamming_threshold,
            min_loop_matches=self.config.min_loop_matches,
            frontend=self.frontend,
        )

    def run(self) -> VIOPipelineResult:
        start = time.perf_counter()
        graph = create_factor_graph()
        ekf = VisualInertialEKF()

        prev_features = None
        prev_ts = None
        prev_pose_idx = 0
        position = np.zeros(3)
        rotation = np.eye(3)

        frame_results: list[FrameResult] = []
        visual_measurements: list[tuple[NDArray[np.float64], NDArray[np.float64]]] = []
        imu_batches: list[list] = []
        timestamps: list[int] = []
        repeatability_scores: list[float] = []
        loop_count = 0
        opt_results: list[OptimizationResult] = []

        graph.add_pose(self.dataset.frames[0].timestamp_ns, position, rotation)
        ekf.initialize(self.dataset.frames[0].timestamp_ns)
        timestamps.append(self.dataset.frames[0].timestamp_ns)

        for i, frame in enumerate(self.dataset.frames):
            features = self.frontend.extract(frame.image)
            num_matches = 0
            is_keyframe = (i % self.config.keyframe_interval == 0) or i == 0

            if prev_features is not None:
                matches = self.frontend.match(prev_features, features)
                num_matches = len(matches)

                if i > 0 and i < len(self.dataset.frames):
                    rep = self.frontend.repeatability(
                        self.dataset.frames[i - 1].image,
                        frame.image,
                    )
                    repeatability_scores.append(rep)

            if is_keyframe and prev_features is not None and prev_ts is not None:
                if num_matches >= self.config.min_matches:
                    avg_parallax = 2.0 + 0.01 * num_matches
                    trans, rel_rot = estimate_visual_odometry(
                        num_matches, self.dataset.intrinsics.fx, avg_parallax
                    )
                    visual_measurements.append((trans, rel_rot))

                    imu_batch = self.dataset.imu_between(prev_ts, frame.timestamp_ns)
                    imu_batches.append(imu_batch)
                    timestamps.append(frame.timestamp_ns)

                    preint = self.preintegrator.integrate(imu_batch)
                    new_idx = graph.add_pose(frame.timestamp_ns, position + trans, rotation @ rel_rot)
                    graph.add_relative_factor(prev_pose_idx, new_idx, trans, rel_rot)
                    graph.add_imu_factor(prev_pose_idx, new_idx, preint)

                    position = position + rotation @ trans
                    rotation = rotation @ rel_rot
                    prev_pose_idx = new_idx

                    if self.config.loop_closure_enabled:
                        kf_obs = [KeyframeObservation(obs) for obs in features]
                        loops = self.loop_detector.add_keyframe(
                            new_idx, frame.timestamp_ns, kf_obs, position, rotation
                        )
                        for loop in loops:
                            graph.add_loop_closure(loop.query_index, loop.match_index, loop.measured_position, loop.measured_rotation)
                            loop_count += 1

            frame_results.append(
                FrameResult(i, frame.timestamp_ns, len(features), num_matches, is_keyframe)
            )
            prev_features = features
            prev_ts = frame.timestamp_ns

        opt_result = graph.optimize()
        opt_results.append(opt_result)

        ekf_result = ekf.run_sequence(timestamps, imu_batches, visual_measurements)

        total_ms = (time.perf_counter() - start) * 1000
        return VIOPipelineResult(
            factor_graph_poses=opt_result.poses,
            ekf_poses=ekf_result.poses,
            frame_results=frame_results,
            optimization_results=opt_results,
            loop_closures=loop_count,
            repeatability_scores=repeatability_scores,
            total_time_ms=total_ms,
            backend_used=opt_result.backend,
        )


def pipeline_config_from_yaml() -> PipelineConfig:
    cfg = load_phase1_config().get("phase1", {})
    lc = cfg.get("loop_closure", {})
    return PipelineConfig(
        keyframe_interval=cfg.get("keyframe_interval", 5),
        min_matches=cfg.get("min_matches", 20),
        loop_closure_enabled=lc.get("enabled", True),
        min_keyframe_gap=lc.get("min_keyframe_gap", 30),
        hamming_threshold=lc.get("hamming_threshold", 50),
        min_loop_matches=lc.get("min_loop_matches", 15),
    )
