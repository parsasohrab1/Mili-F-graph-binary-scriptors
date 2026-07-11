"""Tests for landmark compression."""

import numpy as np

from mili_vio.sharing.compression import COMPRESSED_SIZE, compress_landmark, decompress_landmark
from mili_vio.types import BinaryDescriptor, Landmark


def test_compress_size() -> None:
    lm = Landmark(
        landmark_id=42,
        position=np.array([1.0, 2.0, 3.0]),
        descriptor=BinaryDescriptor(bits=np.random.randint(0, 2, 128, dtype=np.uint8)),
        uncertainty=0.35,
        source_drone_id=3,
        timestamp=1000,
    )
    data = compress_landmark(lm)
    assert len(data) == COMPRESSED_SIZE


def test_roundtrip_no_position() -> None:
    bits = np.array([1, 0] * 64, dtype=np.uint8)
    lm = Landmark(
        landmark_id=7,
        position=np.array([9.0, 8.0, 7.0]),
        descriptor=BinaryDescriptor(bits=bits),
        uncertainty=0.25,
        source_drone_id=2,
        timestamp=500,
    )
    compressed = compress_landmark(lm)
    restored = decompress_landmark(compressed, 2, 500)
    assert restored.landmark_id == 7
    assert np.array_equal(restored.descriptor.bits, bits)
    assert restored.position.sum() == 0  # position not transmitted
