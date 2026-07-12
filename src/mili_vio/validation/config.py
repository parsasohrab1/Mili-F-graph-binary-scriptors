"""Load Phase 6 validation configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[3] / "configs" / "phase6_validation.yaml"


def load_phase6_config(path: Path | str | None = None) -> dict[str, Any]:
    cfg_path = Path(path) if path else default_config_path()
    with cfg_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def phase6_section(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or load_phase6_config()
    return cfg.get("phase6", cfg)
