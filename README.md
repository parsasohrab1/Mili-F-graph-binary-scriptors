# Mili-VIO — Cooperative Visual-Inertial Navigation

**Product 2** — Factor-graph VIO with binary descriptors and event-driven cooperative sharing for GPS-denied multi-drone operations (up to 12 aircraft).

| | |
|---|---|
| **Version** | `0.1.0` (see [CHANGELOG](CHANGELOG.md)) |
| **Python** | ≥ 3.10 |
| **Embedded** | STM32H7 + FreeRTOS |
| **SRS** | [docs/SRS.md](docs/SRS.md) |

## Features

- **FR-1** — Binary descriptor extraction via BNN Product 1 (SPI) or software fallback
- **FR-2** — Sliding-window factor-graph state estimation (GTSAM / SciPy / embedded g2o)
- **FR-3** — Event-driven landmark sharing (≥70% bandwidth reduction target)
- **Integrated runtime** — FR-1 → FR-2 → FR-3 → 69-byte FC output frame @ 20 Hz
- **Embedded firmware** — Host simulation + STM32H7 port (`embedded/`)

## Quick Start

```bash
# Install (desktop algorithms + benchmarks)
pip install -e ".[dev,vio]"

# End-to-end integrated pipeline (synthetic)
mili-vio-run --dataset synthetic --frames 60

# SRS validation suite (Phase 6)
mili-vio-validate --quick --skip-embedded

# Factor-graph vs EKF benchmark
mili-vio-benchmark --dataset synthetic --max-frames 60
```

### Embedded host simulation (Windows / Linux)

```powershell
embedded\scripts\build.ps1 -Quick -Test
```

## CLI Reference

| Command | Purpose |
|---------|---------|
| `mili-vio-run` | Integrated E2E pipeline + FC output |
| `mili-vio-validate` | Phase 6 SRS acceptance orchestrator |
| `mili-vio-benchmark` | FG vs EKF on EuRoC/TUM-VI/synthetic |
| `mili-vio-fr1` | BNN descriptor benchmark + SRS |
| `mili-vio-fr2` | Factor-graph + 4 scenarios |
| `mili-vio-fr3` | Cooperative sharing (2–12 drones) |
| `mili-vio-generate` | Synthetic cooperative dataset CSV |

## Documentation

| Audience | Document |
|----------|----------|
| **Operators** (install, calibrate, flash) | [docs/OPERATOR_GUIDE.md](docs/OPERATOR_GUIDE.md) |
| **Integrators** (FC API, Python, embedded) | [docs/API_INTEGRATION.md](docs/API_INTEGRATION.md) |
| **Validation / acceptance** | [docs/PHASE6_VALIDATION.md](docs/PHASE6_VALIDATION.md) |
| **SRS proof levels** | [docs/SRS_EVIDENCE.md](docs/SRS_EVIDENCE.md) |
| **Release process** | [docs/RELEASE.md](docs/RELEASE.md) |
| Phase 1–5 technical | [docs/PHASE1_BENCHMARK.md](docs/PHASE1_BENCHMARK.md) … [PHASE5_EMBEDDED.md](docs/PHASE5_EMBEDDED.md) |
| Full SRS (Persian) | [docs/SRS.md](docs/SRS.md) |

## Repository Layout

```
src/mili_vio/          Python package (VIO, sharing, runtime, validation)
embedded/              STM32H7 firmware + host simulator
configs/               phase1.yaml … phase6_validation.yaml
tests/                 pytest suite (CI: fast tests; slow: phase6, embedded)
scripts/               download_datasets.py, run_phase6_validation.py
.github/workflows/     CI (pytest + embedded smoke)
```

## Development

```bash
# Fast unit tests (matches GitHub Actions)
pytest tests/ -m "not slow" -v

# Full suite including Phase 6 (~25 min)
pytest tests/ -v

# EuRoC / TUM-VI (optional)
python scripts/download_datasets.py --download
mili-vio-benchmark --dataset MH_01_easy --dataset-root data/datasets
```

## CI/CD

GitHub Actions workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

- **test** — `pytest -m "not slow"` on Python 3.10 / 3.11 (Ubuntu)
- **embedded-smoke** — CMake build + CTest on Windows
- **slow-validation** — `mili-vio-validate --quick` on push to `main`

## License & Product Line

Part of the Mili navigation product family. Depends on **Product 1 (BNN)** for on-chip binary descriptor extraction in production deployments.

---

*For the original Persian SRS specification and acceptance criteria, see [docs/SRS.md](docs/SRS.md).*
