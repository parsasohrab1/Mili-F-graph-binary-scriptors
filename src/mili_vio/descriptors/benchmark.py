"""FR-1 benchmark: extraction time, repeatability, energy."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from mili_vio.descriptors.bnn.api import BNNDescriptorAPI, ExtractionMetrics, load_phase3_config
from mili_vio.vio.datasets.synthetic import generate_synthetic


def _generate_test_sequence(num_frames: int = 10, width: int = 640, height: int = 480) -> list[np.ndarray]:
    dataset = generate_synthetic(num_frames=num_frames, width=width, height=height, seed=42)
    return [f.image for f in dataset.frames]


def run_fr1_benchmark(
    output_dir: Path | str = "data/benchmarks/fr1",
    num_frames: int = 10,
    force_fallback: bool = False,
) -> dict:
    cfg = load_phase3_config()
    api = BNNDescriptorAPI(config=cfg)
    images = _generate_test_sequence(num_frames)

    metrics = api.benchmark_sequence(images)

    single_results = []
    for img in images[:5]:
        r = api.extract(img, force_fallback=force_fallback)
        single_results.append({
            "num_keypoints": r.num_keypoints,
            "time_ms": r.extraction_time_ms,
            "energy_mj": r.energy_mj,
            "source": r.source,
        })

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "fallback" if force_fallback else "bnn",
        "metrics": asdict(metrics),
        "samples": single_results,
        "all_pass": (
            metrics.meets_time_spec
            and metrics.meets_repeatability_spec
            and metrics.meets_energy_spec
        ),
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    label = "fallback" if force_fallback else "bnn"
    path = out / f"fr1_{label}_{ts}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report
