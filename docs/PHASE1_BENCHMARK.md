# Phase 1 — Real VIO Algorithms (Desktop)

## Overview

Phase 1 replaces simulation stubs with real Python VIO algorithms:

- **Visual front-end**: ORB/BRIEF binary descriptors + Hamming matching
- **IMU preintegration**: Forster-style preintegration for factor graph
- **Factor graph**: GTSAM when available; SciPy LM fallback (Windows-compatible)
- **EKF baseline**: For comparative benchmarking
- **Loop closure**: Binary descriptor revisit detection
- **Benchmark + dashboard**: Reproducible evaluation

## Quick Start

```bash
pip install -e ".[dev]"

# Run benchmark on synthetic data (no download needed)
python -m mili_vio.benchmark.cli --dataset synthetic --max-frames 60

# Or via entry point
mili-vio-benchmark --dataset synthetic
```

## EuRoC / TUM-VI Datasets

Download and place sequences under:

```
data/datasets/
  euroc/
    MH_01_easy/mav0/...
  tum_vi/
    dataset-room1_512_16/cam0/...
```

Run:

```bash
mili-vio-benchmark --dataset MH_01_easy --dataset-root data/datasets --max-frames 500
mili-vio-benchmark --dataset dataset-room1_512_16 --dataset-root data/datasets
```

### EuRoC Download

```bash
# Example: MH_01_easy
wget http://robotics.ethz.ch/~asl-datasets/ijrr_euroc_mav_dataset/machine_hall/MH_01_easy/MH_01_easy.zip
unzip MH_01_easy.zip -d data/datasets/euroc/
```

## Acceptance Criteria

| Criterion | Target | Config key |
|-----------|--------|------------|
| Position error (EuRoC) | < 0.5 m | `phase1.benchmark.acceptance_position_error_m` |
| FG vs EKF improvement | ≥ 30% | `phase1.benchmark.acceptance_ekf_improvement_pct` |

Results are saved to `data/benchmarks/benchmark_*.json` and `dashboard_*.png`.

## GTSAM (Optional, Linux)

On Linux where `pip install gtsam` is available, the backend auto-selects GTSAM.
On Windows, SciPy factor-graph optimization is used automatically.

## Module Map

```
src/mili_vio/vio/
  datasets/     EuRoC, TUM-VI, synthetic loaders
  frontend/     ORB/BRIEF + Hamming matching
  backend/      Factor graph (GTSAM/SciPy), EKF baseline
  imu_preintegration.py
  loop_closure.py
  pipeline.py   Offline VIO pipeline

src/mili_vio/benchmark/
  runner.py     Benchmark orchestration
  metrics.py    ATE, position error, comparison
  dashboard.py  Matplotlib error dashboard
```

## Reproducibility

- Seed: `configs/phase1.yaml` → `data_generation.seed` (synthetic)
- Config: `configs/phase1.yaml`
- Output: JSON report with all metrics + PNG dashboard
