"""Tests for optimized binary matching."""

import numpy as np

from mili_vio.descriptors.matching import BinaryMatcher
from mili_vio.types import BinaryDescriptor


def test_batch_hamming() -> None:
    a = np.array([[0, 1] * 64], dtype=np.uint8)
    b = np.array([[0, 0] * 64], dtype=np.uint8)
    dist = BinaryMatcher.batch_hamming(a, b)
    assert dist[0, 0] == 64


def test_match_identical_descriptors() -> None:
    bits = np.array([1, 0] * 64, dtype=np.uint8)
    query = [BinaryDescriptor(bits=bits, keypoint_id=0)]
    train = [BinaryDescriptor(bits=bits.copy(), keypoint_id=0)]
    matcher = BinaryMatcher(hamming_threshold=10)
    matches = matcher.match(query, train)
    assert len(matches) == 1
    assert matches[0].distance == 0


def test_cross_check_matching() -> None:
    matcher = BinaryMatcher(hamming_threshold=50)
    query = [BinaryDescriptor(bits=np.random.randint(0, 2, 128, dtype=np.uint8), keypoint_id=i) for i in range(5)]
    train = [BinaryDescriptor(bits=q.bits.copy(), keypoint_id=i) for i, q in enumerate(query)]
    matches = matcher.match_cross_check(query, train)
    assert len(matches) == 5
