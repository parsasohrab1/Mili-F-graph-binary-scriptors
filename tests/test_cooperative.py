"""Tests for cooperative sharing and multi-drone simulator."""

import numpy as np

from mili_vio.sharing.cooperative import CooperativeCoordinator, MultiDroneSimulator
from mili_vio.sharing.network import SimulatedNetwork
from mili_vio.types import BinaryDescriptor, Landmark


def _landmarks(n: int = 5) -> list[Landmark]:
    return [
        Landmark(
            landmark_id=i,
            position=np.zeros(3),
            descriptor=BinaryDescriptor(bits=np.random.randint(0, 2, 128, dtype=np.uint8)),
            uncertainty=0.2,
            source_drone_id=0,
            timestamp=0,
        )
        for i in range(n)
    ]


def test_event_trigger_below_threshold() -> None:
    net = SimulatedNetwork()
    drone = CooperativeCoordinator(0, network=net)
    result = drone.share_if_needed(0.2, _landmarks(), 1000)
    assert not result.sent


def test_event_trigger_above_threshold() -> None:
    net = SimulatedNetwork()
    drone = CooperativeCoordinator(0, network=net)
    result = drone.share_if_needed(0.5, _landmarks(), 1000)
    assert result.sent
    assert result.bytes_sent > 0
    assert result.latency_ms < 20


def test_multi_drone_simulator() -> None:
    sim = MultiDroneSimulator(num_drones=4)
    sim.steps = 30
    metrics = sim.run()
    assert metrics.events_triggered > 0
    assert metrics.bandwidth_reduction_pct > 0


def test_covariance_trigger() -> None:
    from mili_vio.sharing import EventDrivenSharing
    sharing = EventDrivenSharing()
    assert sharing.should_share_covariance(0.5)  # sqrt(0.5/3) ~ 0.4 > 0.3
    assert not sharing.should_share_covariance(0.01)
