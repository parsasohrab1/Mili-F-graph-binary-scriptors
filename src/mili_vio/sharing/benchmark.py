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
    transport: str = "simulated",
) -> dict:
    cfg = load_sharing_config()
    if "phase3_sharing" in cfg:
        cfg["phase3_sharing"]["transport"] = transport
    if "phase3_sharing" in cfg and "simulation" in cfg["phase3_sharing"]:
        cfg["phase3_sharing"]["simulation"]["steps"] = steps

    from mili_vio.sharing.transport import create_network_transport
    from mili_vio.sharing.network import NetworkConfig

    p3 = cfg.get("phase3_sharing", {})
    net_cfg = p3.get("network", {})
    net = create_network_transport(
        transport,
        NetworkConfig(
            base_port=net_cfg.get("base_port", 7700),
            max_drones=net_cfg.get("max_drones", 12),
        ),
    )
    sim = MultiDroneSimulator(num_drones=num_drones, config=cfg, network=net)
    metrics = sim.run()

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "num_drones": num_drones,
        "steps": steps,
        "transport": transport,
        "is_hardware": net.is_hardware,
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
