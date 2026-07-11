"""Tests for visual front-end."""

import numpy as np
import pytest

from mili_vio.vio.frontend import VisualFrontend


@pytest.fixture
def frontend() -> VisualFrontend:
    return VisualFrontend(descriptor_type="orb", max_features=200)


def test_extract_features(frontend: VisualFrontend) -> None:
    image = np.random.randint(0, 255, (480, 640), dtype=np.uint8)
    features = frontend.extract(image)
    assert len(features) > 0
    assert all(f.descriptor.bits.shape == (128,) for f in features)


def test_hamming_matching(frontend: VisualFrontend) -> None:
    image_a = np.zeros((480, 640), dtype=np.uint8)
    image_a[100:200, 100:200] = 255
    image_b = image_a.copy()
    fa = frontend.extract(image_a)
    fb = frontend.extract(image_b)
    matches = frontend.match(fa, fb)
    assert len(matches) > 0


def test_hamming_distance_descriptors(frontend: VisualFrontend) -> None:
    from mili_vio.types import BinaryDescriptor

    a = BinaryDescriptor(bits=np.array([0, 1] * 64, dtype=np.uint8))
    b = BinaryDescriptor(bits=np.array([0, 0] * 64, dtype=np.uint8))
    matches = frontend.hamming_match_descriptors([a], [b], threshold=128)
    assert len(matches) == 1
    assert matches[0][2] == 64
