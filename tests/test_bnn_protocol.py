"""Tests for BNN protocol."""

import numpy as np

from mili_vio.descriptors.bnn.protocol import (
    BNNCommand,
    BNNFrame,
    BNNStatus,
    ExtractRequest,
    ExtractResponse,
    KeypointResult,
)


def test_frame_encode_decode() -> None:
    frame = BNNFrame(BNNCommand.GET_VERSION, 1, b"\x01\x00\x00")
    encoded = frame.encode()
    decoded = BNNFrame.decode(encoded)
    assert decoded.command == BNNCommand.GET_VERSION
    assert decoded.sequence == 1


def test_extract_response_roundtrip() -> None:
    bits = np.random.randint(0, 2, 128, dtype=np.uint8)
    kp = KeypointResult(100.0, 200.0, 0.5, bits)
    resp = ExtractResponse(BNNStatus.OK, [kp], 1500, 3000)
    payload = resp.to_payload()
    restored = ExtractResponse.from_payload(payload)
    assert restored.status == BNNStatus.OK
    assert len(restored.keypoints) == 1
    assert np.array_equal(restored.keypoints[0].descriptor_bits, bits)


def test_extract_request_payload() -> None:
    req = ExtractRequest(640, 480, 200, b"\x00" * 100)
    payload = req.to_payload()
    assert len(payload) == 6 + 100
