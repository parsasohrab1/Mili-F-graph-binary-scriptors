# SRS Evidence Matrix — Proof vs Simulation

This document maps each SRS acceptance criterion to its **current proof level**.  
Automated report: `mili-vio-validate --evidence-only`

## Proof Levels

| Level | Meaning |
|-------|---------|
| `not_proven` | No measurement run |
| `synthetic` | Simulated data / chip timing model |
| `host_sim` | Embedded desktop simulator (`mili_host_sim`) |
| `real_data` | EuRoC / TUM-VI with ground truth |
| `hardware` | Physical BNN, STM32, or over-the-air radio |

**SRS sign-off requires `real_data` or `hardware` for navigation metrics, and `hardware` for timing on target MCU.**

## Current Status (default checkout, no datasets)

| معیار | SRS | وضعیت فعلی | سطح اثبات |
|--------|-----|------------|-----------|
| خطای موقعیت | < 0.5 m | synthetic PASS ممکن؛ میدان اثبات نشده | `synthetic` |
| خطای جهت | < 2° | همان | `synthetic` |
| استخراج BNN | < 2 ms | زمان chip شبیه‌سازی‌شده | `synthetic` |
| بهینه‌سازی FG | < 5 ms | Python FG + g2o host sim | `synthetic` / `host_sim` |
| کاهش پهنای باند | ≥ 70% | MultiDroneSimulator | `synthetic` |
| بهبود دقت گروهی | ≥ 40% | MultiDroneSimulator | `synthetic` |
| پهنای باند هر پهپاد | ≤ 50 KB/s | `BandwidthManager` فقط Python | `synthetic` |
| تأخیر شبکه | < 50 ms | loopback UDP یا sim | `synthetic` / `host_sim` |
| نرخ تخمین حالت | 20 Hz | `--quick` روی host sim | `host_sim` |
| پایداری | > 1 ساعت | `--stability` اجرا نشده | `not_proven` |

## How to Improve Proof Level

| Target level | Action |
|--------------|--------|
| `real_data` (position/orientation) | `python scripts/download_datasets.py --download` then `mili-vio-benchmark --dataset MH_01_easy` |
| `hardware` (BNN) | `mili-vio-fr1 --validate-srs --transport serial --port COM3` |
| `hardware` (20 Hz) | Flash STM32 firmware, run acceptance on target |
| `hardware` (network) | Fleet test with UWB; log `comm_uwb.c` timestamps |
| Stability | `embedded/build/Release/mili_host_sim.exe --stability` (3600 s) |

## Commands

```bash
# Evidence table + YAML (fast, no embedded build)
mili-vio-validate --evidence-only --quick

# Include embedded 20 Hz proof
mili-vio-validate --evidence-only --include-embedded

# Full Phase 6 + evidence appendix
mili-vio-validate --quick --evidence
```

Output: `data/benchmarks/phase6/srs_evidence_matrix.yaml`

## Gap Summary

| Gap | Blocker |
|-----|---------|
| Navigation on real trajectories | EuRoC/TUM download + benchmark |
| BNN timing on chip | Product 1 hardware + SPI |
| FG < 5 ms on MCU | STM32 HAL + profiler on silicon |
| Bandwidth enforce on air | Firmware rate limiter in `comm_*.c` |
| Fleet 2–12 | Field test (manual checklist in PHASE6_VALIDATION.md) |
| 1-hour stability | Run `--stability` (not in default CI) |

## Relation to Phase 6

`phase6_validation_report.yaml` answers **did automated tests pass?**  
`srs_evidence_matrix.yaml` answers **at what proof level?**

Both are required for honest SRS acceptance review.
