"""Unified runtime: camera/IMU → BNN → factor graph → event-driven sharing."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import yaml
from numpy.typing import NDArray
from scipy.spatial.transform import Rotation

from mili_vio.common.srs_constants import SRS
from mili_vio.config import load_config
from mili_vio.descriptors.bnn.api import BNNDescriptorAPI, ExtractionResult
from mili_vio.factor_graph.estimator import FR2Estimate, FR2FactorGraphEstimator
from mili_vio.runtime.flight_controller import FlightControllerBridge, FlightControllerOutput
from mili_vio.sharing.cooperative import CooperativeCoordinator, ShareResult
from mili_vio.sharing.network import NetworkConfig, SimulatedNetwork
from mili_vio.types import BinaryDescriptor, Landmark, Pose6DOF
from mili_vio.vio.datasets.base import IMUSample, VIODataset
from mili_vio.vio.datasets import load_dataset


def load_integrated_config(path: Path | str | None = None) -> dict:
    if path is None:
        path = Path(__file__).resolve().parents[3] / "configs" / "integrated.yaml"
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class IntegratedFrameResult:
    frame_id: int
    timestamp_ns: int
    extraction: ExtractionResult
    estimate: FR2Estimate
    share_result: ShareResult
    landmarks_received: int
    fc_output: FlightControllerOutput
    skipped: bool = False


@dataclass
class IntegratedRunResult:
    dataset_name: str
    frames_processed: int
    frames_skipped: int
    mean_position_error_m: float
    mean_uncertainty: float
    sharing_events: int
    landmarks_received: int
    mean_extraction_ms: float
    mean_optimization_ms: float
    state_update_hz: float
    meets_position_spec: bool
    frame_results: list[IntegratedFrameResult] = field(default_factory=list)


class IntegratedVIOPipeline:
    """
    Single runtime chaining FR-1 → FR-2 → FR-3 with flight-controller output.

    Data flow::
        Camera/IMU frame
          → BNNDescriptorAPI (FR-1)
          → FR2FactorGraphEstimator (FR-2)
          → CooperativeCoordinator (FR-3, event-driven)
          → FlightControllerBridge (pose + covariance)
    """

    def __init__(
        self,
        drone_id: int = 0,
        config: Optional[dict] = None,
        network: Optional[SimulatedNetwork] = None,
        fc_bridge: Optional[FlightControllerBridge] = None,
    ) -> None:
        self._cfg = config or load_integrated_config()
        self._app = load_config()
        integ = self._cfg.get("integrated", {})

        self.drone_id = drone_id
        self.state_update_hz = integ.get("state_update_hz", SRS.state_update_hz)
        self.state_period_ns = int(1_000_000_000 / self.state_update_hz)
        self.uncertainty_threshold = float(
            integ.get("uncertainty_threshold_m", SRS.uncertainty_threshold_m)
        )
        self.scenario = integ.get("scenario", "open_field")

        self.bnn = BNNDescriptorAPI()
        self.fr2 = FR2FactorGraphEstimator()

        net_cfg = integ.get("network", {})
        self._network = network or SimulatedNetwork(
            NetworkConfig(
                base_port=net_cfg.get("base_port", 7700),
                max_drones=net_cfg.get("max_drones", SRS.max_drones),
                latency_ms=net_cfg.get("latency_ms", 8.0),
            )
        )
        self.sharing = CooperativeCoordinator(
            drone_id=drone_id,
            network=self._network,
            graph=self.fr2.graph,
        )
        self.fc = fc_bridge or FlightControllerBridge()

        self._last_state_ts: int = 0
        self._frame_count = 0
        self._sharing_events = 0
        self._landmarks_received = 0

    def should_update_state(self, timestamp_ns: int) -> bool:
        if self._last_state_ts == 0:
            return True
        return (timestamp_ns - self._last_state_ts) >= self.state_period_ns

    def _build_landmarks(
        self,
        extraction: ExtractionResult,
        uncertainty: float,
        timestamp_ns: int,
    ) -> list[Landmark]:
        landmarks: list[Landmark] = []
        max_lm = self._app.sharing.max_landmarks_shared
        pose = self.fr2.graph.state.poses[-1] if self.fr2.graph.state.poses else None

        for i, (desc, uv) in enumerate(
            zip(extraction.descriptors[:max_lm], extraction.keypoints_uv[:max_lm])
        ):
            if pose is not None:
                depth = 3.0 + 0.1 * i
                position = pose.position + pose.rotation @ np.array([0.0, 0.0, depth])
            else:
                position = np.zeros(3)

            landmarks.append(
                Landmark(
                    landmark_id=i + self._frame_count * 100,
                    position=position,
                    descriptor=desc,
                    uncertainty=uncertainty,
                    source_drone_id=self.drone_id,
                    timestamp=timestamp_ns,
                )
            )
        return landmarks

    def process_frame(
        self,
        timestamp_ns: int,
        image: NDArray[np.uint8],
        imu_samples: list[IMUSample],
        true_pose: Pose6DOF | None = None,
        force: bool = False,
    ) -> IntegratedFrameResult | None:
        """Process one camera frame through the full pipeline."""
        self._frame_count += 1

        if not force and not self.should_update_state(timestamp_ns):
            return None

        self._last_state_ts = timestamp_ns

        extraction = self.bnn.extract(image)
        estimate = self.fr2.process_keyframe_with_features(
            timestamp_ns,
            extraction.keypoints_uv,
            imu_samples,
            true_pose,
            self.scenario,
        )

        landmarks = self._build_landmarks(extraction, estimate.uncertainty, timestamp_ns)
        share_result = self.sharing.share_if_needed(
            estimate.uncertainty, landmarks, timestamp_ns
        )
        if share_result.sent:
            self._sharing_events += 1

        received = self.sharing.receive_and_integrate()
        self._landmarks_received += len(received)

        fc_output = FlightControllerOutput.from_estimate(
            pose=estimate.pose,
            covariance=estimate.covariance,
            uncertainty=estimate.uncertainty,
            timestamp_ns=timestamp_ns,
            optimization_time_ms=estimate.optimization_time_ms,
            sharing_active=share_result.sent or len(received) > 0,
            loop_closure_active=estimate.loop_closure_active,
        )
        self.fc.publish(fc_output)

        return IntegratedFrameResult(
            frame_id=self._frame_count,
            timestamp_ns=timestamp_ns,
            extraction=extraction,
            estimate=estimate,
            share_result=share_result,
            landmarks_received=len(received),
            fc_output=fc_output,
        )

    def run_on_dataset(
        self,
        dataset: VIODataset,
        max_frames: Optional[int] = None,
    ) -> IntegratedRunResult:
        """End-to-end run on EuRoC, TUM-VI, or synthetic dataset."""
        results: list[IntegratedFrameResult] = []
        prev_ts: int | None = None
        skipped = 0
        limit = max_frames or len(dataset.frames)

        for i, frame in enumerate(dataset.frames[:limit]):
            imu_batch = (
                dataset.imu_between(prev_ts or frame.timestamp_ns, frame.timestamp_ns)
                if prev_ts
                else dataset.imu_between(frame.timestamp_ns - 50_000_000, frame.timestamp_ns)
            )

            gt = dataset.ground_truth_at(frame.timestamp_ns)
            true_pose = None
            if gt is not None:
                true_pose = Pose6DOF(
                    position=gt.position.copy(),
                    orientation=Rotation.from_quat(
                        [gt.quaternion[1], gt.quaternion[2], gt.quaternion[3], gt.quaternion[0]]
                    ).as_euler("xyz"),
                )

            result = self.process_frame(
                frame.timestamp_ns, frame.image, imu_batch, true_pose
            )
            if result is None:
                skipped += 1
            else:
                results.append(result)
            prev_ts = frame.timestamp_ns

        return self._compile_run_result(dataset.name, results, skipped)

    def _compile_run_result(
        self,
        dataset_name: str,
        results: list[IntegratedFrameResult],
        skipped: int,
    ) -> IntegratedRunResult:
        if not results:
            return IntegratedRunResult(
                dataset_name=dataset_name,
                frames_processed=0,
                frames_skipped=skipped,
                mean_position_error_m=999.0,
                mean_uncertainty=0.0,
                sharing_events=0,
                landmarks_received=0,
                mean_extraction_ms=0.0,
                mean_optimization_ms=0.0,
                state_update_hz=0.0,
                meets_position_spec=False,
            )

        pos_errors = [
            r.estimate.position_error_m
            for r in results
            if r.estimate.position_error_m > 0
        ]
        mean_pos = float(np.mean(pos_errors)) if pos_errors else 0.0
        mean_unc = float(np.mean([r.estimate.uncertainty for r in results]))
        mean_ext = float(np.mean([r.extraction.extraction_time_ms for r in results]))
        mean_opt = float(np.mean([r.estimate.optimization_time_ms for r in results]))

        duration_s = (results[-1].timestamp_ns - results[0].timestamp_ns) / 1e9
        hz = len(results) / duration_s if duration_s > 0 else 0.0

        target = self._app.accuracy.position_error_target_m
        return IntegratedRunResult(
            dataset_name=dataset_name,
            frames_processed=len(results),
            frames_skipped=skipped,
            mean_position_error_m=mean_pos,
            mean_uncertainty=mean_unc,
            sharing_events=self._sharing_events,
            landmarks_received=self._landmarks_received,
            mean_extraction_ms=mean_ext,
            mean_optimization_ms=mean_opt,
            state_update_hz=hz,
            meets_position_spec=mean_pos < target if pos_errors else False,
            frame_results=results,
        )


class MultiDroneIntegratedRuntime:
    """Cooperative group runtime with shared network (up to 12 drones)."""

    def __init__(self, num_drones: int = 2, config: Optional[dict] = None) -> None:
        self._cfg = config or load_integrated_config()
        integ = self._cfg.get("integrated", {})
        net_cfg = integ.get("network", {})
        self.network = SimulatedNetwork(
            NetworkConfig(
                base_port=net_cfg.get("base_port", 7700),
                max_drones=min(num_drones, SRS.max_drones),
            )
        )
        self.pipelines = [
            IntegratedVIOPipeline(
                drone_id=i,
                config=self._cfg,
                network=self.network,
            )
            for i in range(min(num_drones, SRS.max_drones))
        ]

    def run_on_dataset(
        self,
        dataset: VIODataset,
        max_frames: Optional[int] = None,
    ) -> list[IntegratedRunResult]:
        return [p.run_on_dataset(dataset, max_frames=max_frames) for p in self.pipelines]


def run_integrated(
    dataset_name: str = "synthetic",
    dataset_root: Optional[Path] = None,
    max_frames: Optional[int] = None,
    num_drones: int = 1,
    config: Optional[dict] = None,
) -> IntegratedRunResult | list[IntegratedRunResult]:
    """Load dataset and run integrated pipeline end-to-end."""
    cfg = config or load_integrated_config()
    integ = cfg.get("integrated", {})
    name = dataset_name or integ.get("dataset", "synthetic")
    root = dataset_root or Path(integ.get("dataset_root", "data/datasets"))
    limit = max_frames or integ.get("max_frames", 60)

    dataset = load_dataset(name=name, dataset_root=root, max_frames=limit)

    if num_drones > 1:
        runtime = MultiDroneIntegratedRuntime(num_drones=num_drones, config=cfg)
        return runtime.run_on_dataset(dataset, max_frames=limit)

    pipeline = IntegratedVIOPipeline(config=cfg)
    return pipeline.run_on_dataset(dataset, max_frames=limit)
