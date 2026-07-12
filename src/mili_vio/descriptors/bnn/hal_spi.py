"""SPI/DMA transport layer for BNN Product 1 hardware."""

from __future__ import annotations

import struct
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from mili_vio.descriptors.bnn.protocol import BNNFrame, HEADER_SIZE, PROTOCOL_MAGIC


@dataclass
class SPIDeviceConfig:
    bus_id: int = 0
    cs_pin: int = 0
    clock_hz: int = 20_000_000
    mode: int = 0
    device_path: str = ""


class SPITransport(ABC):
    """Low-level SPI/DMA round-trip to BNN chip (Product 1)."""

    @property
    @abstractmethod
    def is_hardware(self) -> bool:
        ...

    @abstractmethod
    def transact(self, tx_frame: bytes) -> bytes:
        """Send SPI frame and receive response frame."""
        ...

    def ping(self) -> bool:
        try:
            frame = BNNFrame.decode(self.transact(_version_request()))
            return len(frame.payload) >= 3
        except Exception:
            return False


def _version_request() -> bytes:
    from mili_vio.descriptors.bnn.protocol import BNNCommand

    return BNNFrame(BNNCommand.GET_VERSION, 1, b"").encode()


class LoopbackSPITransport(SPITransport):
    """Protocol loopback through local BNN backend (development / CI)."""

    def __init__(self, backend) -> None:
        self._backend = backend

    @property
    def is_hardware(self) -> bool:
        return False

    def transact(self, tx_frame: bytes) -> bytes:
        request = BNNFrame.decode(tx_frame)
        response = self._backend.transact(request)
        return response.encode()


class SPIDevTransport(SPITransport):
    """
    Linux spidev transport for physical BNN chip on SPI bus.

    Requires: pip install spidev (Linux only, /dev/spidev{bus}.{cs})
    """

    def __init__(self, config: SPIDeviceConfig) -> None:
        self.config = config
        self._spi = self._open_spidev()

    @property
    def is_hardware(self) -> bool:
        return True

    def _open_spidev(self):
        try:
            import spidev  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "spidev not installed. On Linux: pip install spidev"
            ) from exc

        bus = self.config.bus_id
        cs = self.config.cs_pin
        spi = spidev.SpiDev()
        path = self.config.device_path or f"/dev/spidev{bus}.{cs}"
        try:
            spi.open(bus, cs)
        except OSError as exc:
            raise RuntimeError(f"Cannot open BNN SPI device {path}: {exc}") from exc
        spi.max_speed_hz = self.config.clock_hz
        spi.mode = self.config.mode
        return spi

    def transact(self, tx_frame: bytes) -> bytes:
        # Read response header first (fixed 8 bytes), then payload length from header
        header_rx = bytes(self._spi.xfer2(list(tx_frame[:HEADER_SIZE])))
        if len(header_rx) < HEADER_SIZE:
            raise RuntimeError("SPI header read failed")
        magic, _cmd, plen, _seq, _flags, _csum = struct.unpack(">HBBHBB", header_rx)
        if magic != PROTOCOL_MAGIC:
            raise RuntimeError(f"BNN SPI bad magic: {magic:#x}")

        remaining_tx = tx_frame[HEADER_SIZE:]
        payload_tx = remaining_tx[:plen]
        pad_len = max(0, plen - len(payload_tx))
        payload_rx = bytes(self._spi.xfer2(list(payload_tx) + [0] * (plen + pad_len)))
        return header_rx + payload_rx[:plen]


class SerialBridgeTransport(SPITransport):
    """
    USB-UART bridge to BNN development board (Product 1).

    Wire format: [4-byte BE length][BNNFrame bytes]

    Requires: pip install pyserial
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 2_000_000,
        timeout_s: float = 0.1,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout_s = timeout_s
        self._ser = self._open_serial()

    @property
    def is_hardware(self) -> bool:
        return True

    def _open_serial(self):
        try:
            import serial  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError("pyserial not installed. pip install pyserial") from exc

        try:
            return serial.Serial(self.port, self.baudrate, timeout=self.timeout_s)
        except serial.SerialException as exc:
            raise RuntimeError(f"Cannot open BNN serial bridge {self.port}: {exc}") from exc

    def transact(self, tx_frame: bytes) -> bytes:
        length_prefix = struct.pack(">I", len(tx_frame))
        self._ser.write(length_prefix + tx_frame)
        self._ser.flush()

        deadline = time.perf_counter() + self.timeout_s
        header = self._ser.read(4)
        while len(header) < 4 and time.perf_counter() < deadline:
            header += self._ser.read(4 - len(header))
        if len(header) < 4:
            raise TimeoutError("BNN serial bridge: no response length")

        resp_len = struct.unpack(">I", header)[0]
        payload = b""
        while len(payload) < resp_len and time.perf_counter() < deadline:
            payload += self._ser.read(resp_len - len(payload))
        if len(payload) < resp_len:
            raise TimeoutError("BNN serial bridge: incomplete response")
        return payload


def create_spi_transport(
    transport: str,
    spi_config: Optional[SPIDeviceConfig] = None,
    backend=None,
    serial_port: str = "",
    serial_baud: int = 2_000_000,
) -> SPITransport:
    """Factory for SPI transport backends."""
    mode = transport.lower()
    if mode in ("simulated", "loopback", "spi"):
        from mili_vio.descriptors.bnn.driver import SimulatedBNNDriver

        sim = backend or SimulatedBNNDriver()
        return LoopbackSPITransport(sim)

    if mode == "spidev":
        cfg = spi_config or SPIDeviceConfig()
        return SPIDevTransport(cfg)

    if mode in ("serial", "uart", "usb"):
        if not serial_port:
            raise ValueError("serial_port required for serial BNN transport")
        return SerialBridgeTransport(serial_port, serial_baud)

    raise ValueError(f"Unknown BNN transport: {transport}")
