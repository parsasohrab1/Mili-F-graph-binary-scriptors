"""SRS constants mirrored from embedded/include/mili/mili_config.h."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SRSConstants:
    """Python mirror of mili_config.h — keep in sync with embedded firmware."""

    cpu_freq_hz: int = 480_000_000
    state_update_hz: int = 20
    state_period_ms: float = 50.0

    cam_width: int = 640
    cam_height: int = 480
    cam_fps: int = 30

    imu_sample_hz: int = 200
    imu_gravity: float = 9.81

    bnn_spi_clock_hz: int = 20_000_000
    bnn_max_keypoints: int = 200
    descriptor_bits: int = 128
    descriptor_bytes: int = 16

    fg_memory_budget: int = 2 * 1024 * 1024
    fg_max_poses: int = 12
    fg_max_landmarks: int = 80
    fg_max_opt_ms: float = 5.0

    uncertainty_threshold_m: float = 0.3
    max_bandwidth_bps: int = 51_200
    max_drones: int = 12
    landmark_compressed_bytes: int = 20

    budget_bnn_ms: float = 2.0
    budget_vio_ms: float = 5.0
    budget_share_ms: float = 20.0

    # Sharing protocol (shared with sharing/protocol.py)
    protocol_magic: int = 0x4D49  # "MI"
    header_size: int = 14

    @property
    def state_period_ns(self) -> int:
        return int(1_000_000_000 / self.state_update_hz)


SRS = SRSConstants()


def verify_embedded_alignment(config_header: Path | None = None) -> dict[str, bool]:
    """Parse mili_config.h and verify Python constants match embedded defines."""
    if config_header is None:
        config_header = (
            Path(__file__).resolve().parents[3]
            / "embedded"
            / "include"
            / "mili"
            / "mili_config.h"
        )
    if not config_header.exists():
        return {"header_found": False}

    text = config_header.read_text(encoding="utf-8")
    checks = {
        "header_found": True,
        "state_update_hz": "MILI_STATE_UPDATE_HZ" in text and f"{SRS.state_update_hz}U" in text,
        "uncertainty_threshold": "MILI_UNCERTAINTY_THRESHOLD 0.3f" in text,
        "landmark_compressed": f"MILI_LANDMARK_COMPRESSED   {SRS.landmark_compressed_bytes}U" in text,
        "max_bandwidth": f"MILI_MAX_BANDWIDTH_BPS     {SRS.max_bandwidth_bps}U" in text,
        "fg_memory": "MILI_FG_MEMORY_BUDGET      (2U * 1024U * 1024U)" in text,
        "descriptor_bits": f"MILI_DESCRIPTOR_BITS       {SRS.descriptor_bits}U" in text,
    }
    return checks
