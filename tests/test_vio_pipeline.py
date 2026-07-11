"""Tests for offline VIO pipeline."""

import numpy as np

from mili_vio.vio.datasets.synthetic import generate_synthetic
from mili_vio.vio.pipeline import OfflineVIOPipeline, PipelineConfig


def test_pipeline_runs_on_synthetic() -> None:
    dataset = generate_synthetic(num_frames=30, seed=42)
    config = PipelineConfig(
        keyframe_interval=3,
        min_matches=5,
        loop_closure_enabled=True,
        min_keyframe_gap=5,
        min_loop_matches=3,
    )
    pipeline = OfflineVIOPipeline(dataset, config=config)
    result = pipeline.run()

    assert len(result.factor_graph_poses) > 0
    assert len(result.ekf_poses) > 0
    assert len(result.frame_results) == 30
    assert result.total_time_ms > 0


def test_pipeline_produces_repeatability_scores() -> None:
    dataset = generate_synthetic(num_frames=20, seed=7)
    pipeline = OfflineVIOPipeline(
        dataset,
        config=PipelineConfig(keyframe_interval=2, min_matches=3, min_keyframe_gap=3, min_loop_matches=2),
    )
    result = pipeline.run()
    assert len(result.repeatability_scores) > 0
