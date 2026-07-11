"""UDP message protocol for cooperative landmark sharing."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np

from mili_vio.types import BinaryDescriptor, Landmark

PROTOCOL_MAGIC = 0x4D49  # "MI"
HEADER_SIZE = 14
COMPRESSED_LANDMARK_SIZE = 20


class MessageType(IntEnum):
    LANDMARK_SHARE = 0x01
    HEARTBEAT = 0x02
    ACK = 0x03


@dataclass
class ShareMetadata:
    drone_id: int
    timestamp_ns: int
    uncertainty: float
    num_landmarks: int
    sequence: int = 0


@dataclass
class LandmarkShareMessage:
    """Sparse landmark share — descriptors + metadata, NOT raw positions."""

    metadata: ShareMetadata
    landmarks: list[Landmark] = field(default_factory=list)
    msg_type: MessageType = MessageType.LANDMARK_SHARE

    @property
    def payload_size(self) -> int:
        return HEADER_SIZE + len(self.landmarks) * COMPRESSED_LANDMARK_SIZE


def encode_header(meta: ShareMetadata, msg_type: MessageType, num_landmarks: int) -> bytes:
    unc_q = int(min(meta.uncertainty, 25.5) * 10)
    return struct.pack(
        ">HBBBIBHBB",
        PROTOCOL_MAGIC,
        1,  # version
        int(msg_type),
        meta.drone_id & 0xFF,
        meta.timestamp_ns & 0xFFFFFFFF,
        num_landmarks & 0xFF,
        unc_q & 0xFFFF,
        meta.sequence & 0xFF,
        0,  # checksum placeholder
    )


def decode_header(data: bytes) -> tuple[MessageType, ShareMetadata]:
    if len(data) < HEADER_SIZE:
        raise ValueError("Header too short")
    magic, ver, mtype, drone_id, ts, n_lm, unc_q, seq, csum = struct.unpack(
        ">HBBBIBHBB", data[:HEADER_SIZE]
    )
    if magic != PROTOCOL_MAGIC:
        raise ValueError(f"Bad magic: {magic:#x}")
    meta = ShareMetadata(
        drone_id=drone_id,
        timestamp_ns=ts,
        uncertainty=unc_q / 10.0,
        num_landmarks=n_lm,
        sequence=seq,
    )
    return MessageType(mtype), meta


def encode_message(msg: LandmarkShareMessage) -> bytes:
    from mili_vio.sharing.compression import compress_landmark

    header = encode_header(msg.metadata, msg.msg_type, len(msg.landmarks))
    body = b"".join(compress_landmark(lm) for lm in msg.landmarks)
    checksum = sum(header[:-1] + body) & 0xFF
    return header[:-1] + bytes([checksum]) + body


def decode_message(data: bytes) -> LandmarkShareMessage:
    from mili_vio.sharing.compression import decompress_landmark

    msg_type, meta = decode_header(data)
    offset = HEADER_SIZE
    landmarks: list[Landmark] = []
    for _ in range(meta.num_landmarks):
        chunk = data[offset : offset + COMPRESSED_LANDMARK_SIZE]
        if len(chunk) < COMPRESSED_LANDMARK_SIZE:
            break
        landmarks.append(decompress_landmark(chunk, meta.drone_id, meta.timestamp_ns))
        offset += COMPRESSED_LANDMARK_SIZE
    return LandmarkShareMessage(metadata=meta, landmarks=landmarks, msg_type=msg_type)
