"""Landmark compression (~20 bytes per landmark)."""

from __future__ import annotations

import struct

import numpy as np

from mili_vio.types import BinaryDescriptor, Landmark

COMPRESSED_SIZE = 20


def compress_landmark(landmark: Landmark) -> bytes:
    """
    Compress landmark to 20 bytes:
      landmark_id(2) + descriptor_packed(16) + uncertainty_q(1) + flags(1)
    Position is NOT transmitted (SRS: sparse landmarks, not raw positions).
    """
    desc_packed = np.packbits(landmark.descriptor.bits[:128])
    if len(desc_packed) < 16:
        desc_packed = np.pad(desc_packed, (0, 16 - len(desc_packed)))
    unc_q = int(min(landmark.uncertainty, 2.55) * 100)
    flags = landmark.source_drone_id & 0x0F
    return struct.pack(">H", landmark.landmark_id & 0xFFFF) + desc_packed[:16].tobytes() + bytes([unc_q, flags])


def decompress_landmark(data: bytes, source_drone_id: int, timestamp: int) -> Landmark:
    if len(data) < COMPRESSED_SIZE:
        raise ValueError("Compressed landmark too short")
    lm_id = struct.unpack(">H", data[:2])[0]
    desc_bytes = data[2:18]
    unc_q, flags = data[18], data[19]
    bits = np.unpackbits(np.frombuffer(desc_bytes, dtype=np.uint8))[:128].astype(np.uint8)
    descriptor = BinaryDescriptor(bits=bits, keypoint_id=lm_id)

    # Position recovered locally via descriptor matching (not sent over network)
    position = np.zeros(3)

    return Landmark(
        landmark_id=lm_id,
        position=position,
        descriptor=descriptor,
        uncertainty=unc_q / 100.0,
        source_drone_id=source_drone_id or (flags & 0x0F),
        timestamp=timestamp,
    )
