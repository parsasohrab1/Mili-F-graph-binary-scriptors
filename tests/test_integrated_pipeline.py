"""Tests for integrated runtime, flight-controller API, and embedded alignment."""

from __future__ import annotations

import numpy as np

from mili_vio.common.srs_constants import SRS, verify_embedded_alignment
from mili_vio.runtime.flight_controller import (
    FC_FRAME_SIZE,
    FlightControllerOutput,
    pack_state_estimate,
    unpack_state_estimate,
)
from mili_vio.runtime.integrated_pipeline import IntegratedVIOPipeline, run_integrated
from mili_vio.sharing.protocol import COMPRESSED_LANDMARK_SIZE, HEADER_SIZE, PROTOCOL_MAGIC
from mili_vio.types import Pose6DOF


def test_srs_constants_match_embedded() -> None:
    checks = verify_embedded_alignment()
    assert checks["header_found"]
    assert all(checks.values())


def test_srs_sharing_protocol_alignment() -> None:
    assert SRS.protocol_magic == PROTOCOL_MAGIC
    assert SRS.header_size == HEADER_SIZE
    assert SRS.landmark_compressed_bytes == COMPRESSED_LANDMARK_SIZE
    assert SRS.uncertainty_threshold_m == 0.3
    assert SRS.state_update_hz == 20


def test_fc_pack_unpack_roundtrip() -> None:
    output = FlightControllerOutput(
        pose=Pose6DOF(
            position=np.array([1.0, 2.0, 3.0]),
            orientation=np.array([0.1, 0.2, 0.3]),
        ),
        uncertainty=0.25,
        covariance_diag=np.array([0.01, 0.02, 0.03, 0.04, 0.05, 0.06]),
        timestamp_us=1_700_000_000_000,
        optimization_time_us=4500,
        sharing_active=True,
        loop_closure_active=False,
    )
    frame = pack_state_estimate(output)
    assert len(frame) == FC_FRAME_SIZE

    restored = unpack_state_estimate(frame)
    assert np.allclose(restored.pose.position, output.pose.position)
    assert np.allclose(restored.pose.orientation, output.pose.orientation)
    assert restored.uncertainty == output.uncertainty
    assert restored.sharing_active
    assert restored.timestamp_us == output.timestamp_us


def test_integrated_pipeline_synthetic() -> None:
    result = run_integrated(dataset_name="synthetic", max_frames=15, num_drones=1)
    assert result.frames_processed > 0
    assert result.mean_extraction_ms >= 0
    assert result.mean_optimization_ms >= 0
    assert result.state_update_hz > 0


def test_integrated_pipeline_single_frame() -> None:
    from mili_vio.vio.datasets.synthetic import generate_synthetic

    dataset = generate_synthetic(num_frames=5)
    pipeline = IntegratedVIOPipeline(drone_id=0)
    frame = dataset.frames[0]
    imu = dataset.imu_between(frame.timestamp_ns - 50_000_000, frame.timestamp_ns)

    result = pipeline.process_frame(frame.timestamp_ns, frame.image, imu, force=True)
    assert result is not None
    assert result.extraction.num_keypoints > 0
    assert result.fc_output.valid
    assert len(pack_state_estimate(result.fc_output)) == FC_FRAME_SIZE


def test_multi_drone_integrated() -> None:
    results = run_integrated(dataset_name="synthetic", max_frames=20, num_drones=2)
    assert isinstance(results, list)
    assert len(results) == 2
    assert all(r.frames_processed > 0 for r in results)
