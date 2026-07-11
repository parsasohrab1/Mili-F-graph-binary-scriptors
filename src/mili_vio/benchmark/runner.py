"""Benchmark runner for Factor-Graph vs EKF comparison."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mili_vio.benchmark.metrics import BenchmarkComparison, compare_methods
from mili_vio.vio.datasets import load_dataset, load_phase1_config
from mili_vio.vio.pipeline import OfflineVIOPipeline, pipeline_config_from_yaml


def run_benchmark(
    dataset_name: str = "synthetic",
    dataset_root: Optional[Path] = None,
    max_frames: Optional[int] = None,
    output_dir: Optional[Path] = None,
) -> BenchmarkComparison:
    cfg = load_phase1_config()
    p1 = cfg.get("phase1", {})
    bench_cfg = p1.get("benchmark", {})

    dataset = load_dataset(name=dataset_name, dataset_root=dataset_root, max_frames=max_frames, config=cfg)
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
        acceptance_error_m=bench_cfg.get("acceptance_position_error_m", 1.0),
        acceptance_improvement_pct=bench_cfg.get("acceptance_ekf_improvement_pct", 30.0),
    )

    out = output_dir or Path(bench_cfg.get("output_dir", "data/benchmarks"))
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = out / f"benchmark_{dataset_name}_{ts}.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(asdict(comparison), f, indent=2)

    return comparison
