"""Run FR-2 across all 4 SRS scenarios."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from mili_vio.factor_graph.estimator import FR2FactorGraphEstimator, load_phase2_config
from mili_vio.vio.datasets.synthetic import generate_synthetic


def run_scenario_benchmark(
    output_dir: Path | str = "data/benchmarks/fr2",
    frames_per_scenario: int = 60,
) -> dict:
    cfg = load_phase2_config()
    scenarios = cfg.get("phase2", {}).get("scenarios", [
        "urban_canyon", "forest_dense", "indoor_complex", "open_field",
    ])

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}
    all_pass = True

    for scenario in scenarios:
        dataset = generate_synthetic(num_frames=frames_per_scenario, seed=hash(scenario) % 10000)
        estimator = FR2FactorGraphEstimator(phase2_config=cfg)
        result = estimator.run_on_dataset(dataset, scenario=scenario, keyframe_interval=3)

        results[scenario] = {
            "mean_position_error_m": result.mean_position_error_m,
            "mean_orientation_error_deg": result.mean_orientation_error_deg,
            "mean_optimization_time_ms": result.mean_optimization_time_ms,
            "max_optimization_time_ms": result.max_optimization_time_ms,
            "loop_closures": result.loop_closures,
            "meets_position_spec": result.meets_position_spec,
            "meets_orientation_spec": result.meets_orientation_spec,
            "meets_optimization_spec": result.meets_optimization_spec,
            "meets_loop_closure_spec": result.meets_loop_closure_spec,
            "memory_within_budget": result.memory_within_budget,
        }

        scenario_pass = all([
            result.meets_position_spec,
            result.meets_orientation_spec,
            result.meets_optimization_spec,
            result.meets_loop_closure_spec,
            result.memory_within_budget,
        ])
        if not scenario_pass:
            all_pass = False

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenarios": results,
        "all_scenarios_pass": all_pass,
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"fr2_scenarios_{ts}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report
