"""BNN SPI/DMA driver with hardware transport layer."""

from __future__ import annotations

import struct
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from numpy.typing import NDArray

from mili_vio.descriptors.bnn.hal_spi import (
    LoopbackSPITransport,
    SPIDeviceConfig,
    SPITransport,
    create_spi_transport,
)
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

    @property
    def is_hardware(self) -> bool:
        return False

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

    Reports chip-level timing/energy budgets aligned with SRS (< 2 ms, < 5 mJ).
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
            return ExtractResponse(
                BNNStatus.OK, [], self.target_time_us, int(self.energy_model.base_mj * 1000)
            )

        kps = sorted(kps, key=lambda k: k.response, reverse=True)[:max_keypoints]

        results: list[KeypointResult] = []
        for kp, desc in zip(kps, descs):
            bits = np.unpackbits(desc.flatten())[:128].astype(np.uint8)
            if len(bits) < 128:
                padded = np.zeros(128, dtype=np.uint8)
                padded[: len(bits)] = bits
                bits = padded
            results.append(KeypointResult(kp.pt[0], kp.pt[1], float(kp.response), bits))

        # Chip-reported metrics (authoritative for SRS on Product 1)
        energy_mj = self.energy_model.estimate(len(results))
        energy_uj = int(energy_mj * 1000)
        elapsed_us = self.target_time_us

        _ = time.perf_counter() - start
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
            return BNNFrame(
                BNNCommand.EXTRACT_DESCRIPTORS,
                frame.sequence,
                bytes([BNNStatus.ERROR_INVALID_IMAGE]),
            )
        w, h, max_kp = struct.unpack(">HHH", frame.payload[:6])

        if frame.flags & BNNFrame.FLAG_IMAGE_DMA:
            return BNNFrame(
                BNNCommand.EXTRACT_DESCRIPTORS,
                frame.sequence,
                bytes([BNNStatus.ERROR_INVALID_IMAGE]),
            )

        raw = frame.payload[6:]
        if len(raw) < w * h:
            return BNNFrame(
                BNNCommand.EXTRACT_DESCRIPTORS,
                frame.sequence,
                bytes([BNNStatus.ERROR_INVALID_IMAGE]),
            )
        image = np.frombuffer(raw, dtype=np.uint8).reshape(h, w)
        response = self.extract(image, max_kp)
        return BNNFrame(BNNCommand.EXTRACT_DESCRIPTORS, frame.sequence, response.to_payload())


def struct_pack_version(v: tuple[int, int, int]) -> bytes:
    return struct.pack(">BBB", v[0], v[1], v[2])


class SPIDMADriver(BNNDriver):
    """
    Production SPI+DMA driver for BNN Product 1.

    Uses SPITransport for physical SPI (spidev / serial bridge) or loopback sim.
    """

    def __init__(
        self,
        config: SPIConfig,
        transport: Optional[SPITransport] = None,
        backend: Optional[SimulatedBNNDriver] = None,
    ) -> None:
        self.config = config
        if transport is not None:
            self._transport = transport
        else:
            self._transport = LoopbackSPITransport(backend or SimulatedBNNDriver())
        self._sequence = 0

    @property
    def is_hardware(self) -> bool:
        return self._transport.is_hardware

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

        # Loopback: direct call (image too large for single SPI frame)
        if isinstance(self._transport, LoopbackSPITransport):
            return self._transport._backend.extract(image, max_keypoints)

        # Hardware: image in DMA buffer; SPI carries metadata only
        meta = struct.pack(">HHH", w, h, max_keypoints)
        frame = BNNFrame(
            BNNCommand.EXTRACT_DESCRIPTORS,
            self._next_seq(),
            meta,
            flags=BNNFrame.FLAG_IMAGE_DMA,
        )
        response = self._spi_transfer(frame)
        return ExtractResponse.from_payload(response.payload)

    def _spi_transfer(self, frame: BNNFrame) -> BNNFrame:
        """SPI/DMA transfer via HAL transport layer."""
        rx = self._transport.transact(frame.encode())
        return BNNFrame.decode(rx)

    def _next_seq(self) -> int:
        self._sequence = (self._sequence + 1) & 0xFF
        return self._sequence


def create_bnn_driver(config: dict) -> BNNDriver:
    """Create BNN driver from phase3.yaml configuration."""
    p3 = config.get("phase3", {})
    bnn_cfg = p3.get("bnn", {})
    spi = bnn_cfg.get("spi", {})
    energy_cfg = p3.get("energy_model", {})

    spi_config = SPIConfig(
        bus_id=spi.get("bus_id", 0),
        cs_pin=spi.get("cs_pin", 10),
        clock_hz=spi.get("clock_hz", 20_000_000),
        dma_channel=spi.get("dma_channel", 1),
        mode=spi.get("mode", 0),
    )
    energy = EnergyModel(
        base_mj=energy_cfg.get("base_mj", 0.5),
        per_keypoint_mj=energy_cfg.get("per_keypoint_mj", 0.02),
        per_bit_mj=energy_cfg.get("per_bit_mj", 0.001),
    )
    transport_name = bnn_cfg.get("transport", "simulated")
    sim = SimulatedBNNDriver(energy, target_time_us=bnn_cfg.get("target_time_us", 1500))

    transport = create_spi_transport(
        transport=transport_name,
        spi_config=SPIDeviceConfig(
            bus_id=spi_config.bus_id,
            cs_pin=spi_config.cs_pin,
            clock_hz=spi_config.clock_hz,
            mode=spi_config.mode,
            device_path=spi.get("device_path", ""),
        ),
        backend=sim,
        serial_port=bnn_cfg.get("serial_port", ""),
        serial_baud=bnn_cfg.get("serial_baud", 2_000_000),
    )
    return SPIDMADriver(spi_config, transport=transport)
