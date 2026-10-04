"""SRS evidence matrix — proof level per acceptance criterion."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

from mili_vio.common.srs_constants import SRS
from mili_vio.validation.config import phase6_section
from mili_vio.validation.datasets import check_datasets


class EvidenceLevel(str, Enum):
    """How strongly a metric is demonstrated."""

    NOT_PROVEN = "not_proven"       # no measurement
    SYNTHETIC = "synthetic"         # simulated / generated data
    HOST_SIM = "host_sim"           # embedded desktop simulator
    REAL_DATA = "real_data"         # EuRoC/TUM-VI with ground truth
    HARDWARE = "hardware"           # physical BNN / MCU / radio


@dataclass
class SRSEvidenceRow:
    metric_id: str
    metric_fa: str
    srs_target: str
    evidence_level: EvidenceLevel
    status_fa: str
    measured: Optional[str]
    meets_spec: Optional[bool]
    source: str
    gap: str


@dataclass
class SRSEvidenceMatrix:
    rows: list[SRSEvidenceRow]
    summary: dict[str, int]

    @property
    def proven_count(self) -> int:
        return sum(1 for r in self.rows if r.evidence_level in (EvidenceLevel.REAL_DATA, EvidenceLevel.HARDWARE))

    @property
    def sim_only_count(self) -> int:
        return sum(
            1 for r in self.rows
            if r.evidence_level in (EvidenceLevel.SYNTHETIC, EvidenceLevel.HOST_SIM)
        )


def _level_status(level: EvidenceLevel, meets: Optional[bool]) -> str:
    labels = {
        EvidenceLevel.NOT_PROVEN: "Not proven",
        EvidenceLevel.SYNTHETIC: "Simulation only",
        EvidenceLevel.HOST_SIM: "host sim",
        EvidenceLevel.REAL_DATA: "Real data (GT)",
        EvidenceLevel.HARDWARE: "Hardware",
    }
    base = labels.get(level, str(level))
    if meets is True:
        return f"{base} — PASS"
    if meets is False:
        return f"{base} — FAIL"
    return base


def evaluate_srs_evidence(
    quick: bool = True,
    dataset_root: Optional[Path] = None,
    run_measurements: bool = True,
    include_embedded: bool = False,
) -> SRSEvidenceMatrix:
    """
    Build SRS evidence matrix with optional quick measurements.

  Does not claim field-hardware proof; classifies what is actually demonstrated.
    """
    p6 = phase6_section()
    root = Path(dataset_root or p6.get("dataset_root", "data/datasets"))
    rows: list[SRSEvidenceRow] = []

    # --- defaults (not proven until measured) ---
    pos_level = EvidenceLevel.NOT_PROVEN
    pos_measured: Optional[str] = None
    pos_meets: Optional[bool] = None
    orient_level = EvidenceLevel.NOT_PROVEN
    orient_measured: Optional[str] = None
    orient_meets: Optional[bool] = None
    bnn_level = EvidenceLevel.SYNTHETIC
    bnn_measured: Optional[str] = None
    bnn_meets: Optional[bool] = None
    fg_level = EvidenceLevel.SYNTHETIC
    fg_measured: Optional[str] = None
    fg_meets: Optional[bool] = None
    bw_red_level = EvidenceLevel.SYNTHETIC
    bw_red_measured: Optional[str] = None
    bw_red_meets: Optional[bool] = None
    acc_imp_level = EvidenceLevel.SYNTHETIC
    acc_imp_measured: Optional[str] = None
    acc_imp_meets: Optional[bool] = None
    bw_cap_level = EvidenceLevel.SYNTHETIC
    bw_cap_measured: Optional[str] = None
    bw_cap_meets: Optional[bool] = None
    net_lat_level = EvidenceLevel.NOT_PROVEN
    net_lat_measured: Optional[str] = None
    net_lat_meets: Optional[bool] = None
    hz_level = EvidenceLevel.NOT_PROVEN
    hz_measured: Optional[str] = None
    hz_meets: Optional[bool] = None
    stab_level = EvidenceLevel.NOT_PROVEN
    stab_measured: Optional[str] = None
    stab_meets: Optional[bool] = None

    ds_status = check_datasets(root)
    has_real = any(d.present and d.has_ground_truth for d in ds_status.datasets)

    if run_measurements:
        from mili_vio.vio.datasets.synthetic import generate_synthetic
        from mili_vio.factor_graph.srs_validation import validate_on_dataset

        frames = 12 if quick else 40
        syn = generate_synthetic(num_frames=frames, seed=42)
        fr2_syn = validate_on_dataset(syn, scenario="open_field", keyframe_interval=5)

        pos_level = EvidenceLevel.SYNTHETIC
        pos_measured = f"{fr2_syn.mean_position_error_m:.3f} m (synthetic)"
        pos_meets = fr2_syn.meets_position_spec

        orient_level = EvidenceLevel.SYNTHETIC
        orient_measured = f"{fr2_syn.mean_orientation_error_deg:.2f} deg (synthetic)"
        orient_meets = fr2_syn.meets_orientation_spec

        fg_level = EvidenceLevel.SYNTHETIC
        fg_measured = f"max {fr2_syn.max_optimization_time_ms:.2f} ms (Python FG)"
        fg_meets = fr2_syn.meets_optimization_spec

        if has_real:
            from mili_vio.vio.datasets import load_dataset

            name = next(d.name for d in ds_status.datasets if d.present and d.has_ground_truth)
            try:
                real_ds = load_dataset(name=name, dataset_root=root, max_frames=frames)
                fr2_real = validate_on_dataset(real_ds, scenario="open_field", keyframe_interval=5)
                pos_level = EvidenceLevel.REAL_DATA
                pos_measured = f"{fr2_real.mean_position_error_m:.3f} m ({name})"
                pos_meets = fr2_real.meets_position_spec
                orient_level = EvidenceLevel.REAL_DATA
                orient_measured = f"{fr2_real.mean_orientation_error_deg:.2f} deg ({name})"
                orient_meets = fr2_real.meets_orientation_spec
            except FileNotFoundError:
                pass

        from mili_vio.descriptors.bnn.hw_validation import validate_bnn_srs

        fr1 = validate_bnn_srs(num_frames=frames, transport="simulated")
        bnn_level = EvidenceLevel.HARDWARE if fr1.is_hardware else EvidenceLevel.SYNTHETIC
        bnn_measured = f"max chip {fr1.max_chip_time_ms:.2f} ms"
        bnn_meets = fr1.meets_time_spec

        from mili_vio.sharing.srs_validation import validate_fr3_srs

        fr3 = validate_fr3_srs(num_drones=4, steps=30 if quick else 80, transport="simulated")
        bw_red_level = EvidenceLevel.SYNTHETIC
        bw_red_measured = f"{fr3.bandwidth_reduction_pct:.1f}%"
        bw_red_meets = fr3.meets_bandwidth_spec
        acc_imp_level = EvidenceLevel.SYNTHETIC
        acc_imp_measured = f"{fr3.accuracy_improvement_pct:.1f}%"
        acc_imp_meets = fr3.meets_accuracy_spec

        from mili_vio.sharing.bandwidth import BandwidthManager

        mgr = BandwidthManager(max_bytes_per_sec=SRS.max_bandwidth_bps)
        # token bucket enforces budget in software sim
        bw_cap_level = EvidenceLevel.SYNTHETIC
        ok = mgr.can_send(40_000) and not mgr.can_send(60_000)
        mgr.record_send(40_000)
        rep = mgr.report()
        bw_cap_measured = f"limiter {SRS.max_bandwidth_bps} B/s, rate={rep.bytes_per_sec:.0f}"
        bw_cap_meets = ok and rep.within_budget

        try:
            fr3_udp = validate_fr3_srs(num_drones=2, steps=20, transport="udp")
            net_lat_level = EvidenceLevel.HOST_SIM if fr3_udp.is_hardware else EvidenceLevel.SYNTHETIC
            net_lat_measured = f"mean {fr3_udp.mean_sharing_latency_ms:.1f} ms (loopback UDP)"
            net_lat_meets = fr3_udp.mean_sharing_latency_ms < 50.0
        except OSError:
            net_lat_measured = "UDP transport unavailable"

        # embedded host sim (optional — slow)
        if include_embedded:
            try:
                from mili_vio.validation.embedded import run_embedded_validation

                emb = run_embedded_validation(quick=True)
                if emb.acceptance_ok:
                    hz_level = EvidenceLevel.HOST_SIM
                    hz_measured = "20 Hz PASS (mili_host_sim --quick)"
                    hz_meets = True
                    fg_embed = "see VIO max us in acceptance stdout"
                    if emb.acceptance_stdout and "VIO max time:" in emb.acceptance_stdout:
                        for line in emb.acceptance_stdout.splitlines():
                            if "VIO max time:" in line:
                                fg_embed = line.strip()
                                break
                    if fg_level == EvidenceLevel.SYNTHETIC:
                        fg_level = EvidenceLevel.HOST_SIM
                        fg_measured = fg_embed
                        fg_meets = True
            except OSError:
                pass

    rows = [
        SRSEvidenceRow(
            metric_id="position_error",
            metric_fa="Position error",
            srs_target="< 0.5 m",
            evidence_level=pos_level,
            status_fa=_level_status(pos_level, pos_meets),
            measured=pos_measured,
            meets_spec=pos_meets,
            source="validate_on_dataset / mili-vio-fr2",
            gap="Needed: full EuRoC/TUM + GPS-denied field test",
        ),
        SRSEvidenceRow(
            metric_id="orientation_error",
            metric_fa="Orientation error",
            srs_target="< 2 deg",
            evidence_level=orient_level,
            status_fa=_level_status(orient_level, orient_meets),
            measured=orient_measured,
            meets_spec=orient_meets,
            source="FR2 orientation_error_deg",
            gap="Needed: real data + calibrated IMU extrinsics",
        ),
        SRSEvidenceRow(
            metric_id="bnn_extraction",
            metric_fa="BNN extraction",
            srs_target=f"< {SRS.budget_bnn_ms} ms",
            evidence_level=bnn_level,
            status_fa=_level_status(bnn_level, bnn_meets),
            measured=bnn_measured,
            meets_spec=bnn_meets,
            source="mili-vio-fr1 --validate-srs",
            gap="Needed: Product 1 on real SPI (--transport serial/spidev)",
        ),
        SRSEvidenceRow(
            metric_id="fg_optimization",
            metric_fa="FG optimization",
            srs_target=f"< {SRS.fg_max_opt_ms} ms",
            evidence_level=fg_level,
            status_fa=_level_status(fg_level, fg_meets),
            measured=fg_measured,
            meets_spec=fg_meets,
            source="FR2 Python / embedded g2o_embedded profiler",
            gap="Needed: STM32H7 with real HAL (not host sim)",
        ),
        SRSEvidenceRow(
            metric_id="bandwidth_reduction",
            metric_fa="Bandwidth reduction",
            srs_target=">= 70%",
            evidence_level=bw_red_level,
            status_fa=_level_status(bw_red_level, bw_red_meets),
            measured=bw_red_measured,
            meets_spec=bw_red_meets,
            source="mili-vio-fr3 cooperative sim",
            gap="Needed: measurement on a real UWB/Wi-Fi radio",
        ),
        SRSEvidenceRow(
            metric_id="group_accuracy",
            metric_fa="Group accuracy improvement",
            srs_target=">= 40%",
            evidence_level=acc_imp_level,
            status_fa=_level_status(acc_imp_level, acc_imp_meets),
            measured=acc_imp_measured,
            meets_spec=acc_imp_meets,
            source="MultiDroneSimulator",
            gap="Needed: group flight of 2–12 drones with field GT",
        ),
        SRSEvidenceRow(
            metric_id="per_drone_bandwidth",
            metric_fa="Per-drone bandwidth",
            srs_target=f"<= {SRS.max_bandwidth_bps // 1024} KB/s",
            evidence_level=bw_cap_level,
            status_fa=_level_status(bw_cap_level, bw_cap_meets),
            measured=bw_cap_measured,
            meets_spec=bw_cap_meets,
            source="BandwidthManager (Python token bucket)",
            gap="Needed: enforce in firmware comm_uwb.c / comm_wifi.c",
        ),
        SRSEvidenceRow(
            metric_id="network_latency",
            metric_fa="Network latency",
            srs_target="< 50 ms",
            evidence_level=net_lat_level,
            status_fa=_level_status(net_lat_level, net_lat_meets),
            measured=net_lat_measured,
            meets_spec=net_lat_meets,
            source="FR3 UDP loopback or SimulatedNetwork",
            gap="Needed: inter-drone latency in the field",
        ),
        SRSEvidenceRow(
            metric_id="state_update_hz",
            metric_fa="State estimation rate",
            srs_target=f"{SRS.state_update_hz} Hz",
            evidence_level=hz_level,
            status_fa=_level_status(hz_level, hz_meets),
            measured=hz_measured,
            meets_spec=hz_meets,
            source="embedded acceptance.c / mili_host_sim",
            gap="Needed: firmware on STM32H7 + real FreeRTOS",
        ),
        SRSEvidenceRow(
            metric_id="stability",
            metric_fa="Stability",
            srs_target="> 1 hour",
            evidence_level=stab_level,
            status_fa=_level_status(stab_level, stab_meets),
            measured=stab_measured or "3600s test not run",
            meets_spec=stab_meets,
            source="mili_host_sim --stability",
            gap="Run: embedded/build/.../mili_host_sim.exe --stability",
        ),
    ]

    summary: dict[str, int] = {}
    for level in EvidenceLevel:
        summary[level.value] = sum(1 for r in rows if r.evidence_level == level)

    return SRSEvidenceMatrix(rows=rows, summary=summary)


def save_srs_evidence(matrix: SRSEvidenceMatrix, output_dir: Path | str) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "srs_evidence_matrix.yaml"
    data = {
        "proven_real_or_hw": matrix.proven_count,
        "sim_or_host_only": matrix.sim_only_count,
        "not_proven": matrix.summary.get(EvidenceLevel.NOT_PROVEN.value, 0),
        "summary_by_level": matrix.summary,
        "rows": [
            {
                **asdict(r),
                "evidence_level": r.evidence_level.value,
            }
            for r in matrix.rows
        ],
    }
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
    return path


def _level_status_en(level: EvidenceLevel, meets: Optional[bool]) -> str:
    labels = {
        EvidenceLevel.NOT_PROVEN: "not proven",
        EvidenceLevel.SYNTHETIC: "sim only",
        EvidenceLevel.HOST_SIM: "host sim",
        EvidenceLevel.REAL_DATA: "real data",
        EvidenceLevel.HARDWARE: "hardware",
    }
    base = labels.get(level, str(level))
    if meets is True:
        return f"{base} PASS"
    if meets is False:
        return f"{base} FAIL"
    return base


def print_srs_evidence_table(matrix: SRSEvidenceMatrix) -> None:
    """Print ASCII table (English labels for console compatibility)."""
    sep = "+" + "-" * 22 + "+" + "-" * 10 + "+" + "-" * 22 + "+"
    print()
    print(sep)
    print(f"| {'metric':<20} | {'SRS':<8} | {'status':<20} |")
    print(sep)
    for r in matrix.rows:
        mid = r.metric_id[:20]
        tgt = r.srs_target[:8]
        st = _level_status_en(r.evidence_level, r.meets_spec)[:20]
        print(f"| {mid:<20} | {tgt:<8} | {st:<20} |")
    print(sep)
    print("\nMeasurements:")
    for r in matrix.rows:
        if r.measured:
            spec = "PASS" if r.meets_spec else ("FAIL" if r.meets_spec is False else "-")
            print(f"  {r.metric_id}: {r.measured} [{spec}]")
