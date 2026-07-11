"""Tests for UDP sharing protocol."""

import numpy as np

from mili_vio.sharing.protocol import (
    COMPRESSED_LANDMARK_SIZE,
    HEADER_SIZE,
    LandmarkShareMessage,
    ShareMetadata,
    decode_message,
    encode_message,
)
from mili_vio.types import BinaryDescriptor, Landmark


def _sample_message() -> LandmarkShareMessage:
    lm = Landmark(
        landmark_id=1,
        position=np.zeros(3),
        descriptor=BinaryDescriptor(bits=np.ones(128, dtype=np.uint8)),
        uncertainty=0.4,
        source_drone_id=0,
        timestamp=100,
    )
    return LandmarkShareMessage(
        metadata=ShareMetadata(0, 1000, 0.45, 1),
        landmarks=[lm],
    )


def test_encode_decode_roundtrip() -> None:
    msg = _sample_message()
    encoded = encode_message(msg)
    decoded = decode_message(encoded)
    assert decoded.metadata.drone_id == 0
    assert len(decoded.landmarks) == 1
    assert decoded.landmarks[0].landmark_id == 1


def test_message_size() -> None:
    msg = _sample_message()
    encoded = encode_message(msg)
    assert len(encoded) == HEADER_SIZE + COMPRESSED_LANDMARK_SIZE
