"""BNN SPI communication protocol definitions (Product 1)."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

import numpy as np
from numpy.typing import NDArray

PROTOCOL_MAGIC = 0xB1B1  # BNN protocol marker
HEADER_SIZE = 8
MAX_PAYLOAD_BYTES = 4096


class BNNCommand(IntEnum):
    NOP = 0x00
    RESET = 0x01
    GET_STATUS = 0x02
    EXTRACT_DESCRIPTORS = 0x10
    SET_CONFIG = 0x11
    GET_VERSION = 0x12


class BNNStatus(IntEnum):
    OK = 0x00
    BUSY = 0x01
    ERROR_INVALID_IMAGE = 0x10
    ERROR_TIMEOUT = 0x11
    ERROR_DMA = 0x12


@dataclass(frozen=True)
class BNNFrame:
    """SPI frame: magic(2) + cmd(1) + len(2) + seq(1) + flags(1) + checksum(1) + payload."""

    command: BNNCommand
    sequence: int
    payload: bytes
    flags: int = 0

    def encode(self) -> bytes:
        header = struct.pack(
            ">HBBHBB",
            PROTOCOL_MAGIC,
            int(self.command),
            len(self.payload),
            self.sequence & 0xFF,
            self.flags,
            0,
        )
        checksum = sum(header[:-1] + self.payload) & 0xFF
        return header[:-1] + bytes([checksum]) + self.payload

    @classmethod
    def decode(cls, data: bytes) -> BNNFrame:
        if len(data) < HEADER_SIZE:
            raise ValueError("Frame too short")
        magic, cmd, plen, seq, flags, csum = struct.unpack(">HBBHBB", data[:HEADER_SIZE])
        if magic != PROTOCOL_MAGIC:
            raise ValueError(f"Invalid magic: {magic:#x}")
        payload = data[HEADER_SIZE : HEADER_SIZE + plen]
        expected = sum(data[:7] + payload) & 0xFF
        if csum != expected:
            raise ValueError("Checksum mismatch")
        return cls(BNNCommand(cmd), seq, payload, flags)


@dataclass(frozen=True)
class ExtractRequest:
    width: int
    height: int
    max_keypoints: int
    image_data: bytes

    def to_payload(self) -> bytes:
        return struct.pack(">HHH", self.width, self.height, self.max_keypoints) + self.image_data


@dataclass
class KeypointResult:
    x: float
    y: float
    response: float
    descriptor_bits: NDArray[np.uint8]  # 128 bits


@dataclass
class ExtractResponse:
    status: BNNStatus
    keypoints: list[KeypointResult]
    extraction_time_us: int
    energy_uj: int

    @classmethod
    def from_payload(cls, payload: bytes) -> ExtractResponse:
        if len(payload) < 11:
            return cls(BNNStatus.ERROR_INVALID_IMAGE, [], 0, 0)
        status_val, n_kp, time_us, energy_uj = struct.unpack(">BHI I", payload[:11])
        offset = 11
        keypoints: list[KeypointResult] = []
        entry_size = 4 + 4 + 4 + 16  # x, y, response, 128-bit desc packed as 16 bytes
        for _ in range(n_kp):
            if offset + entry_size > len(payload):
                break
            x, y, resp = struct.unpack(">fff", payload[offset : offset + 12])
            desc_bytes = payload[offset + 12 : offset + 28]
            bits = np.unpackbits(np.frombuffer(desc_bytes, dtype=np.uint8))[:128].astype(np.uint8)
            keypoints.append(KeypointResult(x, y, resp, bits))
            offset += entry_size
        return cls(BNNStatus(status_val), keypoints, time_us, energy_uj)

    def to_payload(self) -> bytes:
        header = struct.pack(
            ">BHI I",
            int(self.status),
            len(self.keypoints),
            self.extraction_time_us,
            self.energy_uj,
        )
        parts = [header]
        for kp in self.keypoints:
            packed = np.packbits(kp.descriptor_bits[:128]).tobytes()
            if len(packed) < 16:
                packed = packed + b"\x00" * (16 - len(packed))
            parts.append(struct.pack(">fff", kp.x, kp.y, kp.response) + packed[:16])
        return b"".join(parts)
