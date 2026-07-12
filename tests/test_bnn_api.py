"""Tests for BNN driver and API."""

import numpy as np
import cv2

from mili_vio.descriptors.bnn.api import BNNDescriptorAPI
from mili_vio.descriptors.bnn.hal_spi import LoopbackSPITransport
from mili_vio.descriptors.bnn.driver import SimulatedBNNDriver, SPIDMADriver, SPIConfig
from mili_vio.descriptors.bnn.protocol import BNNStatus


def _test_image() -> np.ndarray:
    img = np.zeros((480, 640), dtype=np.uint8)
    img[100:300, 100:400] = 255
    cv2.rectangle(img, (200, 150), (400, 350), 128, 2)
    return img


def test_simulated_driver_extracts() -> None:
    driver = SimulatedBNNDriver()
    result = driver.extract(_test_image(), max_keypoints=50)
    assert result.status == BNNStatus.OK
    assert len(result.keypoints) > 0
    assert all(len(kp.descriptor_bits) == 128 for kp in result.keypoints)


def test_spi_driver_via_protocol() -> None:
    transport = LoopbackSPITransport(SimulatedBNNDriver())
    driver = SPIDMADriver(SPIConfig(), transport=transport)
    result = driver.extract(_test_image(), max_keypoints=30)
    assert result.status == BNNStatus.OK
    assert len(result.keypoints) <= 30


def test_bnn_api_extract() -> None:
    api = BNNDescriptorAPI()
    result = api.extract(_test_image())
    assert result.num_keypoints > 0
    assert result.num_keypoints <= 200
    assert all(d.bits.shape == (128,) for d in result.descriptors)
    assert result.source == "bnn"


def test_fallback_extract() -> None:
    api = BNNDescriptorAPI()
    result = api.extract(_test_image(), force_fallback=True)
    assert result.source == "fallback"
    assert result.num_keypoints > 0


def test_max_keypoints_limit() -> None:
    api = BNNDescriptorAPI()
    result = api.extract(_test_image(), max_keypoints=10)
    assert result.num_keypoints <= 10
