"""Tests for BNN HAL, hardware validation, and SRS metrics."""

import numpy as np
import cv2

from mili_vio.descriptors.bnn.api import BNNDescriptorAPI, load_phase3_config
from mili_vio.descriptors.bnn.driver import (
    SPIDMADriver,
    SPIConfig,
    SimulatedBNNDriver,
    create_bnn_driver,
)
from mili_vio.descriptors.bnn.hal_spi import LoopbackSPITransport
from mili_vio.descriptors.bnn.hw_validation import validate_bnn_srs
from mili_vio.descriptors.bnn.protocol import BNNStatus


def _test_image() -> np.ndarray:
    img = np.zeros((480, 640), dtype=np.uint8)
    img[100:300, 100:400] = 255
    cv2.rectangle(img, (200, 150), (400, 350), 128, 2)
    return img


def test_spi_driver_via_hal_transport() -> None:
    transport = LoopbackSPITransport(SimulatedBNNDriver())
    driver = SPIDMADriver(SPIConfig(), transport=transport)
    result = driver.extract(_test_image(), max_keypoints=30)
    assert result.status == BNNStatus.OK
    assert len(result.keypoints) <= 30
    assert result.extraction_time_us < 2000
    assert not driver.is_hardware


def test_create_bnn_driver_factory() -> None:
    cfg = load_phase3_config()
    driver = create_bnn_driver(cfg)
    assert driver.get_version() == (1, 0, 0)


def test_chip_reported_timing_in_api() -> None:
    api = BNNDescriptorAPI()
    result = api.extract(_test_image())
    assert result.extraction_time_ms < 2.0
    assert result.energy_mj < 5.0


def test_srs_validation_simulated() -> None:
    report = validate_bnn_srs(num_frames=10, transport="simulated")
    assert report.meets_time_spec
    assert report.meets_energy_spec
    assert report.frames_tested == 10
    assert not report.hardware_connected
