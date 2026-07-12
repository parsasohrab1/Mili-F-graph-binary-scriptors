"""Flight-controller output API for main STM32H7 integration."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from numpy.typing import NDArray

from mili_vio.types import Pose6DOF

FC_FRAME_MAGIC = 0xFC01
FC_FRAME_VERSION = 1
FC_FRAME_SIZE = 69

FC_FLAG_VALID = 0x01
FC_FLAG_SHARING_ACTIVE = 0x02
FC_FLAG_LOOP_CLOSURE = 0x04


@dataclass
class FlightControllerOutput:
    """Pose + covariance output for the primary flight controller."""

    pose: Pose6DOF
    uncertainty: float
    covariance_diag: NDArray[np.float64]  # shape (6,) — position + orientation diagonal
    timestamp_us: int
    optimization_time_us: int
    sharing_active: bool = False
    loop_closure_active: bool = False
    valid: bool = True

    @classmethod
    def from_estimate(
        cls,
        pose: Pose6DOF,
        covariance: NDArray[np.float64],
        uncertainty: float,
        timestamp_ns: int,
        optimization_time_ms: float,
        sharing_active: bool = False,
        loop_closure_active: bool = False,
    ) -> FlightControllerOutput:
        cov = np.asarray(covariance, dtype=np.float64)
        if cov.ndim == 2:
            diag = np.diag(cov)[:6]
        else:
            diag = cov[:6]
        if len(diag) < 6:
            diag = np.pad(diag, (0, 6 - len(diag)))

        return cls(
            pose=pose,
            uncertainty=uncertainty,
            covariance_diag=diag.astype(np.float64),
            timestamp_us=timestamp_ns // 1000,
            optimization_time_us=int(optimization_time_ms * 1000),
            sharing_active=sharing_active,
            loop_closure_active=loop_closure_active,
        )


def _checksum(data: bytes) -> int:
    result = 0
    for b in data:
        result ^= b
    return result & 0xFF


def pack_state_estimate(output: FlightControllerOutput) -> bytes:
    """
    Pack state for UART/SPI transfer to main STM32H7 flight controller.

    Wire format matches embedded/include/mili/fc_output.h (69 bytes, little-endian).
    """
    flags = FC_FLAG_VALID if output.valid else 0
    if output.sharing_active:
        flags |= FC_FLAG_SHARING_ACTIVE
    if output.loop_closure_active:
        flags |= FC_FLAG_LOOP_CLOSURE

    cov = output.covariance_diag
    if len(cov) < 6:
        cov = np.pad(cov, (0, 6 - len(cov)))

    body = struct.pack(
        "<HBBQfffffffffffffI",
        FC_FRAME_MAGIC,
        FC_FRAME_VERSION,
        flags,
        output.timestamp_us & 0xFFFFFFFFFFFFFFFF,
        float(output.pose.position[0]),
        float(output.pose.position[1]),
        float(output.pose.position[2]),
        float(output.pose.orientation[0]),
        float(output.pose.orientation[1]),
        float(output.pose.orientation[2]),
        float(output.uncertainty),
        float(cov[0]),
        float(cov[1]),
        float(cov[2]),
        float(cov[3]),
        float(cov[4]),
        float(cov[5]),
        output.optimization_time_us & 0xFFFFFFFF,
    )
    return body + bytes([_checksum(body)])


def unpack_state_estimate(data: bytes) -> FlightControllerOutput:
    """Unpack flight-controller frame from embedded firmware or bridge."""
    if len(data) < FC_FRAME_SIZE:
        raise ValueError(f"Frame too short: {len(data)} < {FC_FRAME_SIZE}")

    payload = data[: FC_FRAME_SIZE - 1]
    if _checksum(payload) != data[FC_FRAME_SIZE - 1]:
        raise ValueError("Checksum mismatch")

    (
        magic,
        _version,
        flags,
        ts_us,
        px,
        py,
        pz,
        roll,
        pitch,
        yaw,
        uncertainty,
        c0,
        c1,
        c2,
        c3,
        c4,
        c5,
        opt_us,
    ) = struct.unpack("<HBBQfffffffffffffI", payload)

    if magic != FC_FRAME_MAGIC:
        raise ValueError(f"Bad magic: {magic:#x}")

    return FlightControllerOutput(
        pose=Pose6DOF(
            position=np.array([px, py, pz], dtype=np.float64),
            orientation=np.array([roll, pitch, yaw], dtype=np.float64),
        ),
        uncertainty=uncertainty,
        covariance_diag=np.array([c0, c1, c2, c3, c4, c5], dtype=np.float64),
        timestamp_us=ts_us,
        optimization_time_us=opt_us,
        sharing_active=bool(flags & FC_FLAG_SHARING_ACTIVE),
        loop_closure_active=bool(flags & FC_FLAG_LOOP_CLOSURE),
        valid=bool(flags & FC_FLAG_VALID),
    )


class FlightControllerBridge:
    """
    Bridge between VIO pipeline and main flight controller.

    Registers a callback or writes packed frames to a transport function.
    """

    def __init__(
        self,
        transport: Optional[Callable[[bytes], None]] = None,
    ) -> None:
        self._transport = transport
        self._last_output: Optional[FlightControllerOutput] = None
        self.frames_sent = 0

    def publish(self, output: FlightControllerOutput) -> bytes:
        """Pack and optionally send state to flight controller."""
        frame = pack_state_estimate(output)
        self._last_output = output
        self.frames_sent += 1
        if self._transport is not None:
            self._transport(frame)
        return frame

    @property
    def last_output(self) -> Optional[FlightControllerOutput]:
        return self._last_output
