"""BNN SPI/DMA driver with simulated backend for desktop development."""

from __future__ import annotations

import struct
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from numpy.typing import NDArray

from mili_vio.descriptors.bnn.protocol import (
    BNNCommand,
    BNNFrame,
    BNNStatus,
    ExtractRequest,
    ExtractResponse,
    KeypointResult,
)


@dataclass
class SPIConfig:
    bus_id: int = 0
    cs_pin: int = 10
    clock_hz: int = 20_000_000
    dma_channel: int = 1
    mode: int = 0


@dataclass
class EnergyModel:
    base_mj: float = 0.5
    per_keypoint_mj: float = 0.02
    per_bit_mj: float = 0.001

    def estimate(self, num_keypoints: int, num_bits: int = 128) -> float:
        return self.base_mj + num_keypoints * self.per_keypoint_mj + num_bits * self.per_bit_mj


class BNNDriver(ABC):
    """Abstract BNN hardware driver."""

    @abstractmethod
    def reset(self) -> BNNStatus:
        ...

    @abstractmethod
    def get_version(self) -> tuple[int, int, int]:
        ...

    @abstractmethod
    def extract(
        self,
        image: NDArray[np.uint8],
        max_keypoints: int = 200,
    ) -> ExtractResponse:
        ...


class SimulatedBNNDriver(BNNDriver):
    """
    Simulated BNN device for development without hardware.

    Uses FAST+ORB internally but exposes the same SPI protocol as real BNN.
    """

    def __init__(
        self,
        energy_model: Optional[EnergyModel] = None,
        target_time_us: int = 1500,
    ) -> None:
        self.energy_model = energy_model or EnergyModel()
        self.target_time_us = target_time_us
        self._sequence = 0
        self._orb = cv2.ORB_create(nfeatures=200, scoreType=cv2.ORB_HARRIS_SCORE)

    def reset(self) -> BNNStatus:
        self._sequence = 0
        return BNNStatus.OK

    def get_version(self) -> tuple[int, int, int]:
        return (1, 0, 0)

    def extract(
        self,
        image: NDArray[np.uint8],
        max_keypoints: int = 200,
    ) -> ExtractResponse:
        start = time.perf_counter()

        if image.ndim != 2:
            return ExtractResponse(BNNStatus.ERROR_INVALID_IMAGE, [], 0, 0)

        kps, descs = self._orb.detectAndCompute(image, None)

        if descs is None or not kps:
            elapsed_us = int((time.perf_counter() - start) * 1_000_000)
            return ExtractResponse(BNNStatus.OK, [], elapsed_us, 0)

        kps = sorted(kps, key=lambda k: k.response, reverse=True)[:max_keypoints]

        results: list[KeypointResult] = []
        for kp, desc in zip(kps, descs):
            bits = np.unpackbits(desc.flatten())[:128].astype(np.uint8)
            if len(bits) < 128:
                padded = np.zeros(128, dtype=np.uint8)
                padded[: len(bits)] = bits
                bits = padded
            results.append(KeypointResult(kp.pt[0], kp.pt[1], float(kp.response), bits))

        elapsed_us = int((time.perf_counter() - start) * 1_000_000)
        energy_mj = self.energy_model.estimate(len(results))
        energy_uj = int(energy_mj * 1000)

        return ExtractResponse(BNNStatus.OK, results, elapsed_us, energy_uj)

    def transact(self, frame: BNNFrame) -> BNNFrame:
        """SPI transaction handler (protocol layer)."""
        self._sequence = frame.sequence
        if frame.command == BNNCommand.RESET:
            self.reset()
            return BNNFrame(BNNCommand.RESET, frame.sequence, bytes([BNNStatus.OK]))
        if frame.command == BNNCommand.GET_VERSION:
            v = self.get_version()
            return BNNFrame(BNNCommand.GET_VERSION, frame.sequence, struct_pack_version(v))
        if frame.command == BNNCommand.EXTRACT_DESCRIPTORS:
            return self._handle_extract(frame)
        return BNNFrame(frame.command, frame.sequence, bytes([BNNStatus.ERROR_INVALID_IMAGE]))

    def _handle_extract(self, frame: BNNFrame) -> BNNFrame:
        if len(frame.payload) < 6:
            return BNNFrame(BNNCommand.EXTRACT_DESCRIPTORS, frame.sequence, bytes([BNNStatus.ERROR_INVALID_IMAGE]))
        w, h, max_kp = struct.unpack(">HHH", frame.payload[:6])
        raw = frame.payload[6:]
        image = np.frombuffer(raw, dtype=np.uint8).reshape(h, w)
        response = self.extract(image, max_kp)
        return BNNFrame(BNNCommand.EXTRACT_DESCRIPTORS, frame.sequence, response.to_payload())


def struct_pack_version(v: tuple[int, int, int]) -> bytes:
    return struct.pack(">BBB", v[0], v[1], v[2])


class SPIDMADriver(BNNDriver):
    """
    Production SPI+DMA driver interface.

    On STM32H7 this wraps HAL_SPI_TransmitReceive_DMA.
    Desktop: delegates to SimulatedBNNDriver.
    """

    def __init__(self, config: SPIConfig, backend: Optional[BNNDriver] = None) -> None:
        self.config = config
        self._backend = backend or SimulatedBNNDriver()
        self._sequence = 0

    def reset(self) -> BNNStatus:
        frame = BNNFrame(BNNCommand.RESET, self._next_seq(), b"")
        response = self._spi_transfer(frame)
        return BNNStatus(response.payload[0]) if response.payload else BNNStatus.ERROR_DMA

    def get_version(self) -> tuple[int, int, int]:
        frame = BNNFrame(BNNCommand.GET_VERSION, self._next_seq(), b"")
        response = self._spi_transfer(frame)
        if len(response.payload) >= 3:
            return (response.payload[0], response.payload[1], response.payload[2])
        return (0, 0, 0)

    def extract(
        self,
        image: NDArray[np.uint8],
        max_keypoints: int = 200,
    ) -> ExtractResponse:
        h, w = image.shape[:2]
        request = ExtractRequest(w, h, max_keypoints, image.tobytes())
        frame = BNNFrame(BNNCommand.EXTRACT_DESCRIPTORS, self._next_seq(), request.to_payload())
        response = self._spi_transfer(frame)
        return ExtractResponse.from_payload(response.payload)

    def _spi_transfer(self, frame: BNNFrame) -> BNNFrame:
        """SPI/DMA transfer — simulated on desktop, HAL on embedded."""
        if isinstance(self._backend, SimulatedBNNDriver):
            return self._backend.transact(frame)
        raise NotImplementedError("Hardware SPI not available on this platform")

    def _next_seq(self) -> int:
        self._sequence = (self._sequence + 1) & 0xFF
        return self._sequence
