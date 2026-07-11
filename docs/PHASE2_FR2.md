# Phase 2 — FR-2: Factor-Graph State Estimation

## Overview

Complete FR-2 implementation with sliding-window factor graph:

| Component | Module |
|-----------|--------|
| Pose + landmark nodes | `factor_graph/nodes.py` |
| IMU / reprojection / loop factors | `factor_graph/factors.py` |
| Sliding window + memory budget | `factor_graph/sliding_window.py` |
| Fast optimizer (< 5ms target) | `factor_graph/optimizer.py` |
| Covariance + uncertainty | `factor_graph/covariance.py` |
| FR-2 estimator | `factor_graph/estimator.py` |

## SRS Acceptance Criteria

| Metric | Target | Config |
|--------|--------|--------|
| Position error | < 0.5 m | `phase2.accuracy.position_error_target_m` |
| Orientation error | < 2° | `phase2.accuracy.orientation_error_target_deg` |
| Optimization time | < 5 ms | `phase2.optimization.max_time_ms` |
| Loop closure | Active | `phase2.loop_closure.enabled` |
| Memory | ≤ 2 MB | `phase2.sliding_window.memory_budget_bytes` |

## Usage

```bash
# Run 4-scenario SRS benchmark
mili-vio-fr2 --frames 60

# Or
python -m mili_vio.factor_graph.cli --frames 60
```

## Graph Structure

```
Pose nodes:    X_0, X_1, ..., X_n  (6-DOF each)
Landmark nodes: L_0, L_1, ..., L_m  (3D position)

Factors:
  - IMU preintegration:     X_i -- X_j
  - Visual reprojection:    X_i -- L_j (2D observation)
  - Loop closure:           X_i -- X_j (retrospective)
```

## Uncertainty Output (Phase 4)

Each `FR2Estimate` includes:
- `covariance`: 6×6 pose covariance
- `uncertainty`: scalar metric from position block (√(trace/3))

Used by event-driven sharing (FR-3) when uncertainty > 0.3 m.

## Configuration

See `configs/phase2.yaml` for scenario noise profiles and window sizes.
