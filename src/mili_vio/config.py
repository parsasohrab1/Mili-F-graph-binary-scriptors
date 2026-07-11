"""Configuration loader aligned with SRS specifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SystemConfig:
    max_drones_per_group: int = 12
    state_update_rate_hz: int = 20
    max_bandwidth_bytes_per_sec: int = 51200


@dataclass
class HardwareConfig:
    image_width: int = 640
    image_height: int = 480
    camera_fps: int = 30
    descriptor_bits: int = 128
    max_keypoints: int = 200
    factor_graph_memory_mb: int = 2


@dataclass
class AccuracyConfig:
    position_error_target_m: float = 0.5
    orientation_error_target_deg: float = 2.0
    uncertainty_threshold_m: float = 0.3


@dataclass
class PerformanceConfig:
    descriptor_extraction_max_ms: float = 2.0
    optimization_max_ms: float = 5.0
    sharing_latency_max_ms: float = 20.0
    network_latency_max_ms: float = 50.0


@dataclass
class CommQualityWeight:
    name: str
    probability: float


@dataclass
class DataGenerationConfig:
    seed: int = 2026
    num_groups: int = 15
    drones_per_group: int = 6
    time_steps: int = 600
    base_timestamp: int = 1700000000
    scenarios: list[str] = field(
        default_factory=lambda: [
            "urban_canyon",
            "forest_dense",
            "indoor_complex",
            "open_field",
        ]
    )
    communication_qualities: list[CommQualityWeight] = field(
        default_factory=lambda: [
            CommQualityWeight("clear", 0.5),
            CommQualityWeight("intermittent", 0.3),
            CommQualityWeight("jammed", 0.2),
        ]
    )


@dataclass
class SharingConfig:
    landmark_bytes_compressed: int = 20
    min_landmarks_shared: int = 3
    max_landmarks_shared: int = 15
    improvement_factor_min: float = 0.2
    improvement_factor_max: float = 0.35


@dataclass
class AppConfig:
    system: SystemConfig = field(default_factory=SystemConfig)
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    accuracy: AccuracyConfig = field(default_factory=AccuracyConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    data_generation: DataGenerationConfig = field(default_factory=DataGenerationConfig)
    sharing: SharingConfig = field(default_factory=SharingConfig)


def _merge_dataclass(cls: type, data: dict[str, Any]) -> Any:
    if not data:
        return cls()
    field_types = {f.name: f.type for f in cls.__dataclass_fields__.values()}
    kwargs: dict[str, Any] = {}
    for key, value in data.items():
        if key not in field_types:
            continue
        if key == "communication_qualities" and isinstance(value, list):
            kwargs[key] = [CommQualityWeight(**item) for item in value]
        else:
            kwargs[key] = value
    return cls(**kwargs)


def load_config(path: Path | str | None = None) -> AppConfig:
    if path is None:
        path = Path(__file__).resolve().parents[2] / "configs" / "default.yaml"
    else:
        path = Path(path)

    if not path.exists():
        return AppConfig()

    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return AppConfig(
        system=_merge_dataclass(SystemConfig, raw.get("system", {})),
        hardware=_merge_dataclass(HardwareConfig, raw.get("hardware", {})),
        accuracy=_merge_dataclass(AccuracyConfig, raw.get("accuracy", {})),
        performance=_merge_dataclass(PerformanceConfig, raw.get("performance", {})),
        data_generation=_merge_dataclass(DataGenerationConfig, raw.get("data_generation", {})),
        sharing=_merge_dataclass(SharingConfig, raw.get("sharing", {})),
    )
