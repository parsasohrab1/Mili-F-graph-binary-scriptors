# Phase 6 — SRS Acceptance Validation

Phase 6 unifies desktop algorithms (Phases 1–3), integrated runtime (Phase 4), and embedded firmware (Phase 5) into a single **SRS acceptance report**.

## Quick Start

```bash
pip install -e ".[dev,vio]"

# Fast CI validation (~2 min, synthetic + simulated)
mili-vio-validate --quick --skip-embedded

# Full automated suite including embedded C build + CTest
mili-vio-validate --full

# Check / download EuRoC + TUM-VI
python scripts/download_datasets.py --check
python scripts/download_datasets.py --download
mili-vio-validate --full --download
```

Report written to: `data/benchmarks/phase6/phase6_validation_report.yaml`

## Acceptance Matrix

| Item | Automated | Target | Command / module |
|------|-----------|--------|------------------|
| **FG vs EKF (4 scenarios)** | Yes | pos < 0.5 m, FG ≥30% better than EKF | `validation/scenario_matrix.py` |
| **FG vs EKF (EuRoC/TUM-VI)** | Yes* | Same, on real GT | `mili-vio-benchmark` / scenario_matrix |
| **FR-1 BNN SRS** | Yes (sim) | < 2 ms, > 90% repeatability, < 5 mJ | `validate_bnn_srs()` |
| **FR-2 factor graph SRS** | Yes | 4 scenarios + optional real data | `validate_fr2_srs()` |
| **FR-3 cooperative 2–12 drones** | Yes (sim) | bandwidth ≥70%, accuracy ≥40%, latency <20 ms | `validate_drone_group_sweep()` |
| **Embedded 20 Hz** | Yes | 20 Hz, ≤2 MB, no crashes | `embedded/scripts/build.ps1 -Quick` |
| **Embedded C unit tests** | Yes | factor_graph, memory, pipeline | `ctest --test-dir embedded/build` |
| **GPS-denied field flight** | **Manual** | Outdoor VIO without GPS | See Field Test Checklist |
| **Fleet 2–12 field test** | **Manual** | Cooperative sharing in air | See Field Test Checklist |

\* Requires downloaded datasets under `data/datasets/`.

## EuRoC / TUM-VI Datasets

### Layout

```
data/datasets/
  euroc/
    MH_01_easy/mav0/cam0/data.csv + data/*.png
    MH_02_easy/...
    V1_01_easy/...
  tum_vi/
    dataset-room1_512_16/cam0/data.csv + data/*.png
```

### Download

```bash
python scripts/download_datasets.py --download
# or manual (EuRoC example):
wget http://robotics.ethz.ch/~asl-datasets/ijrr_euroc_mav_dataset/machine_hall/MH_01_easy/MH_01_easy.zip
unzip MH_01_easy.zip -d data/datasets/euroc/
```

Configured sequences: `configs/phase6_validation.yaml` → `datasets.euroc_sequences` / `tum_vi_sequences`.

### SRS-grade real-data benchmark

When datasets are present, Phase 6 runs **FG vs EKF** with ground-truth alignment (ATE) on each sequence. This is the SRS-grade benchmark (not the synthetic noise abstraction).

```bash
mili-vio-benchmark --dataset MH_01_easy --dataset-root data/datasets --max-frames 500
mili-vio-validate --full --download
```

## Four SRS Scenarios (Synthetic Noise Abstraction)

| Scenario | Noise profile | Purpose |
|----------|---------------|---------|
| `urban_canyon` | Higher visual + IMU noise | Multipath / occlusion |
| `forest_dense` | Medium noise | Feature-poor canopy |
| `indoor_complex` | Highest noise | Weak geometry, drift |
| `open_field` | Lowest noise | Baseline outdoor |

Scenarios are **noise models** applied to synthetic trajectories (see `configs/phase2.yaml`). They are not photorealistic simulators. Real EuRoC machine-hall sequences are tagged separately in the real-data suite.

```bash
mili-vio-fr2 --validate-srs --scenarios-only
mili-vio-validate --quick   # includes FG vs EKF × 4 scenarios
```

## FR-3 Group Test (2–12 Drones)

Simulated cooperative sweep:

```bash
mili-vio-fr3 --validate-srs --12-drones
mili-vio-validate --full    # sweeps [2,4,6,8,10,12]
```

For kernel UDP latency measurements: `mili-vio-fr3 --validate-srs --transport udp`.

## Embedded C Validation

```powershell
# Build + 30s acceptance + CTest
embedded\scripts\build.ps1 -Quick -Test

# 1-hour stability (SRS)
embedded\build\Release\mili_host_sim.exe --stability
```

CMake targets: `test_factor_graph`, `test_memory`, `test_pipeline`.

Python smoke: `pytest tests/test_embedded_build.py`

## Field Test Checklist (Manual — Not in CI)

### GPS-denied flight

- [ ] STM32H7 firmware flashed with production HAL (DCMI, BMI088, BNN SPI)
- [ ] Pre-flight: `mili_host_sim --quick` PASS on release binary
- [ ] Outdoor area with surveyed ground-truth markers or RTK base for post-hoc eval
- [ ] Log FC binary frames (`mili_fc_frame_t`, 69 bytes) + raw IMU/camera timestamps
- [ ] Post-flight: position drift < SRS threshold over mission duration
- [ ] Document wind, lighting, mission profile in acceptance report appendix

### Cooperative fleet (2–12 drones)

- [ ] Each drone: unique `drone_id`, UWB/WiFi UDP ports per `NetworkConfig.base_port`
- [ ] Simultaneous takeoff; shared map origin
- [ ] Measure: sharing latency, bandwidth reduction, group position accuracy vs solo
- [ ] Compare to `validate_drone_group_sweep()` simulated baselines

Record results in `data/benchmarks/phase6/field_test_log.yaml` (manual template).

## Report Schema

`phase6_validation_report.yaml` contains:

```yaml
automated_pass: true/false
srs_grade_real_data: true/false   # true only when EuRoC/TUM benchmarks pass
fg_ekf_scenarios: ...              # 4 synthetic scenarios
fg_ekf_real: ...                   # EuRoC/TUM results
fr1_srs / fr2_srs / fr3_drone_sweep / embedded
field_tests:                       # status: manual
```

## Per-Phase Documentation

| Phase | Doc |
|-------|-----|
| 1 — VIO benchmark | `docs/PHASE1_BENCHMARK.md` |
| 2 — FR-2 factor graph | `docs/PHASE2_FR2.md` |
| 3 — FR-1 BNN + FR-3 sharing | `docs/PHASE3_FR1.md`, `docs/PHASE3_FR3.md` |
| 5 — Embedded | `docs/PHASE5_EMBEDDED.md` |
| **6 — Validation** | **this document** |

## Acceptance Criteria Summary

| Criterion | Target | Config key |
|-----------|--------|------------|
| Position error | < 0.5 m | `phase6.acceptance.position_error_m` |
| FG vs EKF improvement | ≥ 30% | `phase6.acceptance.ekf_improvement_pct` |
| State update rate (embedded) | 20 Hz | `MILI_STATE_UPDATE_HZ` |
| FG memory (embedded) | ≤ 2 MB | `MILI_FG_MEMORY_BUDGET` |
| FR-3 bandwidth reduction | ≥ 70% | `phase3_sharing.acceptance` |
| FR-3 group accuracy gain | ≥ 40% | `phase3_sharing.acceptance` |
| FR-3 sharing latency | < 20 ms | `phase3_sharing.acceptance` |
| Stability (embedded) | 1 hour, 0 crashes | `MILI_STABILITY_MIN_SEC` |

## Known Gaps

| Gap | Status |
|-----|--------|
| EuRoC/TUM auto-download | Script provided; large downloads optional |
| Scenario = real environment | Scenarios are noise abstractions only |
| Field / fleet tests | Manual checklist above |
| GTSAM on Windows | SciPy backend; note in report |
| BNN Product 1 hardware | Use `mili-vio-fr1 --validate-srs --transport serial` |
