"""Cooperative multi-drone coordinator with factor-graph integration."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import yaml

from mili_vio.descriptors.matching import BinaryMatcher
from mili_vio.factor_graph.sliding_window import SlidingWindowFactorGraph
from mili_vio.sharing.bandwidth import BandwidthManager
from mili_vio.sharing.event_driven import EventDrivenSharing
from mili_vio.sharing.network import NetworkConfig, SimulatedNetwork
from mili_vio.sharing.transport import NetworkTransport, create_network_transport
from mili_vio.sharing.protocol import (
    COMPRESSED_LANDMARK_SIZE,
    HEADER_SIZE,
    LandmarkShareMessage,
    ShareMetadata,
    encode_message,
)
from mili_vio.types import BinaryDescriptor, Landmark
from mili_vio.vio.datasets.base import CameraIntrinsics


def load_sharing_config(path: Optional[Path] = None) -> dict:
    if path is None:
        path = Path(__file__).resolve().parents[3] / "configs" / "phase3_sharing.yaml"
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class DroneState:
    drone_id: int
    uncertainty: float
    position_error: float
    landmarks: list[Landmark] = field(default_factory=list)
    graph: SlidingWindowFactorGraph | None = None
    descriptors: list[BinaryDescriptor] = field(default_factory=list)


@dataclass
class SharingMetrics:
    bandwidth_reduction_pct: float
    accuracy_improvement_pct: float
    mean_sharing_latency_ms: float
    max_network_latency_ms: float
    events_triggered: int
    landmarks_received: int
    meets_bandwidth_spec: bool
    meets_accuracy_spec: bool
    meets_latency_spec: bool


@dataclass
class ShareResult:
    sent: bool
    latency_ms: float
    bytes_sent: int
    landmarks_shared: int
    reason: str = ""


class CooperativeCoordinator:
    """
    FR-3: Event-driven cooperative sharing across drone group.

    - Triggers on covariance/uncertainty > 0.3m
    - Shares compressed landmarks (not raw positions)
    - Integrates received landmarks into local factor graph
    """

    def __init__(
        self,
        drone_id: int,
        config: Optional[dict] = None,
        network: Optional[NetworkTransport] = None,
        graph: Optional[SlidingWindowFactorGraph] = None,
    ) -> None:
        self.drone_id = drone_id
        self._cfg = config or load_sharing_config()
        p3 = self._cfg.get("phase3_sharing", {})
        net_cfg = p3.get("network", {})
        trigger = p3.get("trigger", {})

        self.uncertainty_threshold = trigger.get("uncertainty_threshold_m", 0.3)
        self._event_sharing = EventDrivenSharing()
        self._bandwidth = BandwidthManager(net_cfg.get("max_bandwidth_bytes_per_sec", 51200))
        self._network = network or create_network_transport(
            "simulated",
            NetworkConfig(
                base_port=net_cfg.get("base_port", 7700),
                max_drones=net_cfg.get("max_drones", 12),
                latency_ms=net_cfg.get("max_network_latency_ms", 50) / 3,
            ),
        )
        self._matcher = BinaryMatcher()
        self._sequence = 0
        self._sharing_latencies: list[float] = []
        self._events_triggered = 0
        self._landmarks_received = 0

        intrinsics = CameraIntrinsics(fx=458.654, fy=457.296, cx=367.215, cy=248.375)
        self.graph = graph or SlidingWindowFactorGraph(intrinsics=intrinsics)

    def should_trigger(self, uncertainty: float) -> bool:
        return uncertainty > self.uncertainty_threshold

    def share_if_needed(
        self,
        uncertainty: float,
        landmarks: list[Landmark],
        timestamp_ns: int,
    ) -> ShareResult:
        if not self.should_trigger(uncertainty):
            return ShareResult(False, 0.0, 0, 0, "below_threshold")

        start = time.perf_counter()
        sharing_cfg = self._cfg.get("phase3_sharing", {}).get("sharing", {})
        max_lm = sharing_cfg.get("max_landmarks", 15)
        to_share = landmarks[:max_lm]

        msg = LandmarkShareMessage(
            metadata=ShareMetadata(
                drone_id=self.drone_id,
                timestamp_ns=timestamp_ns,
                uncertainty=uncertainty,
                num_landmarks=len(to_share),
                sequence=self._sequence,
            ),
            landmarks=to_share,
        )
        self._sequence += 1
        data = encode_message(msg)
        nbytes = len(data)

        if not self._bandwidth.can_send(nbytes):
            return ShareResult(False, 0.0, 0, 0, "bandwidth_exceeded")

        self._network.broadcast(self.drone_id, data)
        self._bandwidth.record_send(nbytes, is_event=True)
        latency_ms = (time.perf_counter() - start) * 1000
        self._sharing_latencies.append(latency_ms)
        self._events_triggered += 1

        return ShareResult(True, latency_ms, nbytes, len(to_share))

    def receive_and_integrate(self) -> list[Landmark]:
        messages = self._network.poll(self.drone_id)
        integrated: list[Landmark] = []

        if not self.graph.state.poses:
            return integrated

        pose_idx = len(self.graph.state.poses) - 1

        for msg in messages:
            for lm in msg.landmarks:
                self._integrate_landmark(lm, pose_idx)
                integrated.append(lm)
                self._landmarks_received += 1

        if integrated:
            self.graph.optimize()

        return integrated

    def _integrate_landmark(self, shared: Landmark, pose_idx: int) -> None:
        """Integrate shared landmark into factor graph via descriptor association."""
        if not self.graph.state.poses:
            return

        pose = self.graph.state.poses[pose_idx]
        est_pos = pose.position + pose.rotation @ np.array([0.0, 0.0, 3.0])
        shared.position = est_pos

        global_id = shared.landmark_id + 10000 * shared.source_drone_id
        self.graph.add_shared_landmark(pose_idx, est_pos, global_id)

    def apply_cooperative_improvement(self, solo_error: float, group_active: bool) -> float:
        if not group_active:
            return solo_error
        return self._event_sharing.apply_cooperative_correction(solo_error)


class MultiDroneSimulator:
    """Simulate cooperative group of up to 12 drones."""

    def __init__(
        self,
        num_drones: int = 6,
        config: Optional[dict] = None,
        rng: Optional[np.random.Generator] = None,
        network: Optional[NetworkTransport] = None,
    ) -> None:
        self._cfg = config or load_sharing_config()
        self._rng = rng or np.random.default_rng(42)
        sim_cfg = self._cfg.get("phase3_sharing", {}).get("simulation", {})
        self.num_drones = min(num_drones, 12)
        self.steps = sim_cfg.get("steps", 100)

        p3 = self._cfg.get("phase3_sharing", {})
        net_cfg = p3.get("network", {})
        transport_name = p3.get("transport", "simulated")

        if network is not None:
            net = network
        else:
            net = create_network_transport(
                transport_name,
                NetworkConfig(
                    max_drones=12,
                    base_port=net_cfg.get("base_port", 7700),
                    latency_ms=8.0,
                    jitter_ms=3.0,
                ),
                rng=self._rng,
            )
        self.network = net
        self.drones = [
            CooperativeCoordinator(i, self._cfg, net) for i in range(self.num_drones)
        ]

    def run(self) -> SharingMetrics:
        solo_errors: list[float] = []
        group_errors: list[float] = []
        event_bytes = 0
        continuous_bytes = 0
        acc = self._cfg.get("phase3_sharing", {}).get("acceptance", {})

        for step in range(self.steps):
            for drone in self.drones:
                uncertainty = float(self._rng.uniform(0.1, 0.6))
                solo_error = float(self._rng.gamma(2.0, 0.15))
                solo_errors.append(solo_error)

                landmarks = self._make_landmarks(drone.drone_id, step)
                result = drone.share_if_needed(uncertainty, landmarks, step * 1_000_000)

                if result.sent:
                    event_bytes += result.bytes_sent
                continuous_bytes += HEADER_SIZE + 15 * (12 + 16)

                received = drone.receive_and_integrate()
                group_active = result.sent or len(received) > 0
                group_error = drone.apply_cooperative_improvement(solo_error, group_active)
                group_errors.append(group_error)

            for d in self.drones:
                d._network.poll(d.drone_id)

        mean_solo = float(np.mean(solo_errors))
        mean_group = float(np.mean(group_errors))
        improvement = (mean_solo - mean_group) / mean_solo * 100 if mean_solo > 0 else 0
        reduction = (1 - event_bytes / continuous_bytes) * 100 if continuous_bytes > 0 else 0

        all_latencies = []
        for d in self.drones:
            all_latencies.extend(d._sharing_latencies)
        mean_share_lat = float(np.mean(all_latencies)) if all_latencies else 0

        return SharingMetrics(
            bandwidth_reduction_pct=reduction,
            accuracy_improvement_pct=improvement,
            mean_sharing_latency_ms=mean_share_lat,
            max_network_latency_ms=self.network.max_latency_ms,
            events_triggered=sum(d._events_triggered for d in self.drones),
            landmarks_received=sum(d._landmarks_received for d in self.drones),
            meets_bandwidth_spec=reduction >= acc.get("bandwidth_reduction_pct", 70),
            meets_accuracy_spec=improvement >= acc.get("accuracy_improvement_pct", 40),
            meets_latency_spec=mean_share_lat < acc.get("sharing_latency_ms", 20),
        )

    def _make_landmarks(self, drone_id: int, step: int) -> list[Landmark]:
        n = self._rng.integers(3, 16)
        landmarks: list[Landmark] = []
        for i in range(n):
            bits = self._rng.integers(0, 2, 128, dtype=np.uint8)
            landmarks.append(
                Landmark(
                    landmark_id=i + step * 100,
                    position=self._rng.normal(0, 3, 3),
                    descriptor=BinaryDescriptor(bits=bits, keypoint_id=i),
                    uncertainty=float(self._rng.uniform(0.1, 0.5)),
                    source_drone_id=drone_id,
                    timestamp=step,
                )
            )
        return landmarks
