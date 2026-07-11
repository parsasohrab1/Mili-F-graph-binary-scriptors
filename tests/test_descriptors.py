"""Tests for binary descriptor extraction."""

import cv2
import numpy as np
import pytest

from mili_vio.descriptors import BinaryDescriptorExtractor


@pytest.fixture
def extractor() -> BinaryDescriptorExtractor:
    return BinaryDescriptorExtractor(rng=np.random.default_rng(42))


@pytest.fixture
def textured_image() -> np.ndarray:
    img = np.zeros((480, 640), dtype=np.uint8)
    img[100:300, 100:400] = 255
    cv2.rectangle(img, (150, 120), (450, 360), 180, 3)
    for i in range(0, 640, 40):
        cv2.line(img, (i, 0), (i, 480), 80, 1)
    return img


def test_extract_returns_descriptors(extractor: BinaryDescriptorExtractor, textured_image: np.ndarray) -> None:
    descriptors = extractor.extract(textured_image, num_keypoints=10)
    assert len(descriptors) > 0
    assert len(descriptors) <= 10
    assert all(d.bits.shape == (128,) for d in descriptors)


def test_descriptor_bits_are_binary(extractor: BinaryDescriptorExtractor, textured_image: np.ndarray) -> None:
    descriptors = extractor.extract(textured_image, num_keypoints=5)
    for desc in descriptors:
        assert set(desc.bits.tolist()).issubset({0, 1})


def test_descriptor_temporal_variation(extractor: BinaryDescriptorExtractor, textured_image: np.ndarray) -> None:
    shifted = np.roll(textured_image, 5, axis=1)
    first = extractor.extract(textured_image, num_keypoints=20)
    second = extractor.extract(shifted, num_keypoints=20)
    if first and second:
        distances = [first[i].hamming_distance(second[i]) for i in range(min(len(first), len(second)))]
        assert max(distances) < 128


def test_max_keypoints_respected(extractor: BinaryDescriptorExtractor, textured_image: np.ndarray) -> None:
    descriptors = extractor.extract(textured_image, num_keypoints=500)
    assert len(descriptors) <= 200


def test_invalid_image_raises(extractor: BinaryDescriptorExtractor) -> None:
    with pytest.raises(ValueError):
        extractor.extract(np.zeros((480, 640, 3), dtype=np.uint8))


def test_extraction_metrics_available(extractor: BinaryDescriptorExtractor, textured_image: np.ndarray) -> None:
    extractor.extract(textured_image)
    assert extractor.last_extraction_time_ms >= 0
    assert extractor.last_energy_mj >= 0
