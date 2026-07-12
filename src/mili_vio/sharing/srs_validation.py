"""SRS acceptance validation for FR-3 cooperative sharing."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import yaml

from mili_vio.sharing.cooperative import MultiDroneSimulator, SharingMetrics, load_sharing_config
from mili_vio.sharing.network import NetworkConfig
from mili_vio.sharing.transport import NetworkTransport, create_network_transport


@dataclass
class FR3SRSReport:
    transport: str
    is_hardware: bool
    num_drones: int
    steps: int
    bandwidth_reduction_pct: float
    accuracy_improvement_pct: float
    mean_sharing_latency_ms: float
    max_network_latency_ms: float
    events_triggered: int
    landmarks_received: int
    meets_bandwidth_spec: bool
    meets_accuracy_spec: bool
    meets_latency_spec: bool
    all_pass: bool
    notes: list[str]


def validate_fr3_srs(
    num_drones: int = 6,
    steps: int = 100,
    transport: str = "simulated",
    config: Optional[dict] = None,
    host: str = "127.0.0.1",
) -> FR3SRSReport:
    """
    Validate FR-3 SRS acceptance:
      - bandwidth reduction >= 70%
      - group accuracy improvement >= 40%
      - sharing latency < 20 ms
      - up to 12 drones
    """
    cfg = config or load_sharing_config()
    p3 = cfg.get("phase3_sharing", {})
    net_cfg = p3.get("network", {})
    notes: list[str] = []

    num_drones = min(num_drones, net_cfg.get("max_drones", 12))
    network_cfg = NetworkConfig(
        base_port=net_cfg.get("base_port", 7700),
        max_drones=net_cfg.get("max_drones", 12),
        latency_ms=net_cfg.get("max_network_latency_ms", 50) / 3,
    )

    try:
        net: NetworkTransport = create_network_transport(
            transport=transport,
            config=network_cfg,
            host=host,
        )
    except OSError as exc:
        notes.append(f"Transport {transport} failed: {exc} — falling back to simulated")
        net = create_network_transport("simulated", network_cfg)

    if transport not in ("simulated", "sim") and not net.is_hardware:
        notes.append("Hardware transport requested but simulated backend active")

    sim = MultiDroneSimulator(num_drones=num_drones, config=cfg, network=net)
    sim.steps = steps
    metrics: SharingMetrics = sim.run()

    if net.is_hardware:
        notes.append(
            f"Real UDP latency: mean={net.mean_latency_ms:.2f} ms, max={net.max_latency_ms:.2f} ms"
        )
    else:
        notes.append("Using SimulatedNetwork — use --transport udp for kernel UDP measurements")

    return FR3SRSReport(
        transport=transport,
        is_hardware=net.is_hardware,
        num_drones=num_drones,
        steps=steps,
        bandwidth_reduction_pct=metrics.bandwidth_reduction_pct,
        accuracy_improvement_pct=metrics.accuracy_improvement_pct,
        mean_sharing_latency_ms=metrics.mean_sharing_latency_ms,
        max_network_latency_ms=metrics.max_network_latency_ms,
        events_triggered=metrics.events_triggered,
        landmarks_received=metrics.landmarks_received,
        meets_bandwidth_spec=metrics.meets_bandwidth_spec,
        meets_accuracy_spec=metrics.meets_accuracy_spec,
        meets_latency_spec=metrics.meets_latency_spec,
        all_pass=(
            metrics.meets_bandwidth_spec
            and metrics.meets_accuracy_spec
            and metrics.meets_latency_spec
        ),
        notes=notes,
    )


def validate_12_drone_group(steps: int = 80, transport: str = "simulated") -> FR3SRSReport:
    """SRS max group size: 12 drones."""
    return validate_fr3_srs(num_drones=12, steps=steps, transport=transport)


def save_fr3_srs_report(report: FR3SRSReport, output_dir: Path | str) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "fr3_srs_validation.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(asdict(report), f, default_flow_style=False)
    return path
