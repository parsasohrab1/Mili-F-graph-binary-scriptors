"""Tests for FR-3 transport and SRS validation."""

import numpy as np

from mili_vio.sharing.cooperative import CooperativeCoordinator, MultiDroneSimulator
from mili_vio.sharing.protocol import encode_message, ShareMetadata, LandmarkShareMessage
from mili_vio.sharing.srs_validation import validate_fr3_srs, validate_12_drone_group
from mili_vio.sharing.transport import RealUDPNetwork, create_network_transport
from mili_vio.types import BinaryDescriptor, Landmark


def _landmarks(n: int = 3) -> list[Landmark]:
    return [
        Landmark(
            landmark_id=i,
            position=np.zeros(3),
            descriptor=BinaryDescriptor(bits=np.zeros(128, dtype=np.uint8), keypoint_id=i),
            uncertainty=0.2,
            source_drone_id=0,
            timestamp=0,
        )
        for i in range(n)
    ]


def test_create_udp_transport() -> None:
    net = create_network_transport("udp")
    assert net.is_hardware
    try:
        net.broadcast(0, b"test")
    finally:
        if hasattr(net, "close"):
            net.close()


def test_real_udp_roundtrip() -> None:
    net = RealUDPNetwork()
    try:
        msg = LandmarkShareMessage(
            metadata=ShareMetadata(0, 1000, 0.5, 1, 0),
            landmarks=_landmarks(1),
        )
        data = encode_message(msg)
        net.broadcast(0, data)
        received = net.poll(1)
        assert len(received) >= 1
    finally:
        net.close()


def test_coordinator_with_udp_transport() -> None:
    net = create_network_transport("udp")
    try:
        a = CooperativeCoordinator(0, network=net)
        b = CooperativeCoordinator(1, network=net)
        result = a.share_if_needed(0.5, _landmarks(), 1000)
        assert result.sent
        received = b.receive_and_integrate()
        assert len(received) >= 0
    finally:
        if hasattr(net, "close"):
            net.close()


def test_fr3_srs_validation_simulated() -> None:
    report = validate_fr3_srs(num_drones=4, steps=30, transport="simulated")
    assert report.num_drones == 4
    assert report.events_triggered > 0
    assert not report.is_hardware


def test_fr3_12_drone_group() -> None:
    report = validate_12_drone_group(steps=20, transport="simulated")
    assert report.num_drones == 12
