"""FR-2 SRS acceptance validation for factor-graph state estimation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import yaml

from mili_vio.factor_graph.estimator import FR2FactorGraphEstimator, FR2RunResult, load_phase2_config
from mili_vio.vio.backend.gtsam_backend import GTSAM_AVAILABLE
from mili_vio.vio.datasets import load_dataset
from mili_vio.vio.datasets.base import VIODataset
from mili_vio.vio.datasets.synthetic import generate_synthetic


@dataclass
class FR2DatasetReport:
    dataset: str
    scenario: str
    frames: int
    mean_position_error_m: float
    mean_orientation_error_deg: float
    mean_optimization_time_ms: float
    max_optimization_time_ms: float
    loop_closures: int
    max_memory_bytes: int
    memory_budget_bytes: int
    backend: str
    meets_position_spec: bool
    meets_orientation_spec: bool
    meets_optimization_spec: bool
    meets_loop_closure_spec: bool
    meets_memory_spec: bool
    all_pass: bool


@dataclass
class FR2SRSReport:
    reports: list[FR2DatasetReport]
    all_pass: bool
    gtsam_available: bool
    notes: list[str]


def _backend_name() -> str:
    if GTSAM_AVAILABLE:
        return "gtsam"
    return "scipy_factor_graph"


def _max_memory_from_result(result: FR2RunResult, budget: int) -> int:
    if not result.estimates:
        return 0
    return max(e.memory_used_bytes for e in result.estimates)


def validate_on_dataset(
    dataset: VIODataset,
    scenario: str = "open_field",
    keyframe_interval: int = 3,
    config: Optional[dict] = None,
) -> FR2DatasetReport:
    cfg = config or load_phase2_config()
    p2 = cfg.get("phase2", {})
    acc = p2.get("accuracy", {})
    opt = p2.get("optimization", {})
    budget = p2.get("sliding_window", {}).get("memory_budget_bytes", 2 * 1024 * 1024)

    estimator = FR2FactorGraphEstimator(phase2_config=cfg)
    result = estimator.run_on_dataset(dataset, scenario=scenario, keyframe_interval=keyframe_interval)

    max_mem = _max_memory_from_result(result, budget)

    return FR2DatasetReport(
        dataset=dataset.name,
        scenario=scenario,
        frames=len(dataset.frames),
        mean_position_error_m=result.mean_position_error_m,
        mean_orientation_error_deg=result.mean_orientation_error_deg,
        mean_optimization_time_ms=result.mean_optimization_time_ms,
        max_optimization_time_ms=result.max_optimization_time_ms,
        loop_closures=result.loop_closures,
        max_memory_bytes=max_mem,
        memory_budget_bytes=budget,
        backend=_backend_name(),
        meets_position_spec=result.meets_position_spec,
        meets_orientation_spec=result.meets_orientation_spec,
        meets_optimization_spec=result.meets_optimization_spec,
        meets_loop_closure_spec=result.meets_loop_closure_spec,
        meets_memory_spec=result.memory_within_budget and max_mem <= budget,
        all_pass=all([
            result.meets_position_spec,
            result.meets_orientation_spec,
            result.meets_optimization_spec,
            result.meets_loop_closure_spec,
            result.memory_within_budget,
        ]),
    )


def validate_fr2_srs(
    dataset_name: str = "synthetic",
    dataset_root: Optional[Path] = None,
    max_frames: int = 60,
    include_scenarios: bool = True,
    euroc_sequence: Optional[str] = None,
) -> FR2SRSReport:
    """
    Validate FR-2 against SRS acceptance criteria.

    Checks: position < 0.5 m, orientation < 2 deg, optimization < 5 ms,
    loop closure active, memory <= 2 MB.
    """
    cfg = load_phase2_config()
    p2 = cfg.get("phase2", {})
    scenarios = p2.get("scenarios", ["open_field"]) if include_scenarios else ["open_field"]
    notes: list[str] = []
    reports: list[FR2DatasetReport] = []

    if not GTSAM_AVAILABLE:
        notes.append("GTSAM not installed — using SciPy factor-graph backend")

    for scenario in scenarios:
        dataset = generate_synthetic(
            num_frames=max_frames,
            seed=abs(hash(scenario)) % 100_000,
        )
        reports.append(validate_on_dataset(dataset, scenario=scenario, config=cfg))

    # Real dataset validation (EuRoC / TUM-VI) when available
    real_name = euroc_sequence or dataset_name
    if real_name != "synthetic":
        root = dataset_root or Path("data/datasets")
        try:
            real_ds = load_dataset(name=real_name, dataset_root=root, max_frames=max_frames)
            if real_ds.ground_truth:
                reports.append(
                    validate_on_dataset(real_ds, scenario="open_field", keyframe_interval=5, config=cfg)
                )
            else:
                notes.append(f"Dataset {real_name} has no ground truth — skipped pose error")
        except FileNotFoundError:
            notes.append(f"Real dataset '{real_name}' not found under {root}")

    all_pass = all(r.all_pass for r in reports)
    return FR2SRSReport(
        reports=reports,
        all_pass=all_pass,
        gtsam_available=GTSAM_AVAILABLE,
        notes=notes,
    )


def save_fr2_srs_report(report: FR2SRSReport, output_dir: Path | str) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "fr2_srs_validation.yaml"
    data = {
        "all_pass": report.all_pass,
        "gtsam_available": report.gtsam_available,
        "notes": report.notes,
        "reports": [asdict(r) for r in report.reports],
    }
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False)
    return path
