"""FR-3 cooperative sharing benchmark."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from mili_vio.sharing.cooperative import MultiDroneSimulator, load_sharing_config


def run_fr3_benchmark(
    num_drones: int = 6,
    steps: int = 100,
    output_dir: Path | str = "data/benchmarks/fr3",
) -> dict:
    cfg = load_sharing_config()
    if "phase3_sharing" in cfg and "simulation" in cfg["phase3_sharing"]:
        cfg["phase3_sharing"]["simulation"]["steps"] = steps

    sim = MultiDroneSimulator(num_drones=num_drones, config=cfg)
    metrics = sim.run()

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "num_drones": num_drones,
        "steps": steps,
        "metrics": asdict(metrics),
        "all_pass": (
            metrics.meets_bandwidth_spec
            and metrics.meets_accuracy_spec
            and metrics.meets_latency_spec
        ),
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = out / f"fr3_{num_drones}drones_{ts}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report
