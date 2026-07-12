"""FG vs EKF benchmark across SRS scenarios and real datasets."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from mili_vio.benchmark.metrics import BenchmarkComparison, compare_methods
from mili_vio.validation.config import phase6_section
from mili_vio.vio.datasets import load_dataset, load_phase1_config
from mili_vio.vio.datasets.synthetic import generate_synthetic
from mili_vio.vio.pipeline import OfflineVIOPipeline, pipeline_config_from_yaml


@dataclass
class ScenarioMatrixReport:
    scenarios: list[dict]
    real_datasets: list[dict]
    all_scenarios_pass: bool
    all_real_pass: bool
    notes: list[str]

    @property
    def all_pass(self) -> bool:
        return self.all_scenarios_pass and self.all_real_pass


def _run_fg_ekf_on_dataset(
    dataset,
    scenario_label: str,
    acceptance_error_m: float,
    acceptance_improvement_pct: float,
) -> BenchmarkComparison:
    pipeline = OfflineVIOPipeline(dataset, config=pipeline_config_from_yaml())
    result = pipeline.run()
    comparison = compare_methods(
        dataset=dataset,
        fg_poses=result.factor_graph_poses,
        ekf_poses=result.ekf_poses,
        fg_opt_time_ms=sum(r.optimization_time_ms for r in result.optimization_results),
        ekf_time_ms=result.total_time_ms,
        repeatability=result.repeatability_scores,
        loop_closures=result.loop_closures,
        backend=result.backend_used,
        acceptance_error_m=acceptance_error_m,
        acceptance_improvement_pct=acceptance_improvement_pct,
    )
    # Override scenario label for SRS reporting (synthetic noise profile name)
    comparison.scenario = scenario_label
    return comparison


def _comparison_to_dict(c: BenchmarkComparison) -> dict:
    d = asdict(c)
    d["all_pass"] = c.meets_position_spec and c.meets_improvement_spec
    return d


def run_fg_ekf_scenario_matrix(
    max_frames: int = 60,
    config: Optional[dict] = None,
) -> ScenarioMatrixReport:
    """
    Run FG vs EKF on 4 SRS synthetic scenarios (noise abstractions).

    Each scenario uses an independent synthetic trajectory seed.
    """
    p6 = phase6_section(config)
    acc = p6.get("acceptance", {})
    scenarios = p6.get("scenarios", [
        "urban_canyon", "forest_dense", "indoor_complex", "open_field",
    ])
    err_m = acc.get("position_error_m", 0.5)
    imp_pct = acc.get("ekf_improvement_pct", 30.0)

    scenario_rows: list[dict] = []
    all_scenarios_pass = True

    for scenario in scenarios:
        dataset = generate_synthetic(
            num_frames=max_frames,
            seed=abs(hash(scenario)) % 100_000,
        )
        comparison = _run_fg_ekf_on_dataset(dataset, scenario, err_m, imp_pct)
        row = _comparison_to_dict(comparison)
        scenario_rows.append(row)
        if not row["all_pass"]:
            all_scenarios_pass = False

    return ScenarioMatrixReport(
        scenarios=scenario_rows,
        real_datasets=[],
        all_scenarios_pass=all_scenarios_pass,
        all_real_pass=True,
        notes=["Synthetic scenarios use independent seeds; noise model is FR-2 abstraction."],
    )


def run_fg_ekf_real_suite(
    dataset_root: Path,
    max_frames: int = 500,
    config: Optional[dict] = None,
) -> ScenarioMatrixReport:
    """Run FG vs EKF on available EuRoC / TUM-VI sequences (SRS-grade when GT present)."""
    p6 = phase6_section(config)
    acc = p6.get("acceptance", {})
    ds_cfg = p6.get("datasets", {})
    err_m = acc.get("position_error_m", 0.5)
    imp_pct = acc.get("ekf_improvement_pct", 30.0)
    cfg = load_phase1_config()

    real_rows: list[dict] = []
    notes: list[str] = []
    all_real_pass = True

    names = list(ds_cfg.get("euroc_sequences", [])) + list(ds_cfg.get("tum_vi_sequences", []))
    for name in names:
        try:
            dataset = load_dataset(
                name=name,
                dataset_root=dataset_root,
                max_frames=max_frames,
                config=cfg,
            )
        except FileNotFoundError:
            notes.append(f"Skipped {name}: not found under {dataset_root}")
            all_real_pass = False
            continue

        if not dataset.ground_truth:
            notes.append(f"Skipped {name}: no ground truth for ATE")
            all_real_pass = False
            continue

        comparison = _run_fg_ekf_on_dataset(dataset, name, err_m, imp_pct)
        row = _comparison_to_dict(comparison)
        real_rows.append(row)
        if not row["all_pass"]:
            all_real_pass = False

    if not real_rows:
        notes.append("No real datasets benchmarked — download with scripts/download_datasets.py")

    return ScenarioMatrixReport(
        scenarios=[],
        real_datasets=real_rows,
        all_scenarios_pass=True,
        all_real_pass=all_real_pass if real_rows else False,
        notes=notes,
    )
