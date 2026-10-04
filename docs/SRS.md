# SRS — Mili-VIO Cooperative Navigation System (Product 2)

> Software Requirements Specification (SRS). For operational setup see [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md) and for the integration API see [API_INTEGRATION.md](API_INTEGRATION.md).

## 1. Introduction

### 1.1 Purpose

A cooperative navigation system for a drone swarm using a Factor Graph, a binary descriptor (BNN Product 1), and event-driven sharing in a GPS-denied environment.

### 1.2 Scope

- GPS-independent VIO (camera + IMU)
- Cooperation of 2–12 drones
- Target position error: **< 0.5 m** (normal conditions)
- State update rate: **20 Hz**

### 1.3 Terminology

| Acronym | Meaning |
|--------|------|
| VIO | Visual-Inertial Odometry |
| FG | Factor Graph |
| EKF | Extended Kalman Filter |
| BNN | Binary Neural Network (Product 1) |

## 2. Architecture

```
Drone swarm (≤12) ──► Event-driven Landmark sharing
       │
       ▼
  VIO MCU (STM32H7): Camera → BNN → FG → Sharing → FC frame (69 B)
```

## 3. Hardware Requirements

| Component | Specification |
|--------|--------|
| MCU | STM32H7, 480 MHz |
| Camera | Global shutter 640×480 @ 30 fps |
| IMU | Bosch BMI088 |
| RAM FG | ≤ 2 MB |
| Communication | UWB / Wi-Fi, latency < 50 ms |

## 4. Functional Requirements

### FR-1: Binary Descriptor

| Criterion | Target |
|--------|-----|
| Extraction time | < 2 ms |
| Repeatability | > 90% |
| Energy | < 5 mJ/frame |
| Output | 128-bit × ≤200 keypoints |

**Implementation:** `src/mili_vio/descriptors/bnn/`, `embedded/src/drivers/bnn_spi.c`

### FR-2: Factor Graph

| Criterion | Target |
|--------|-----|
| Position error | < 0.5 m |
| Orientation error | < 2° |
| Optimization time | < 5 ms |
| Memory | ≤ 2 MB |
| Loop closure | Enabled |

**SRS scenarios:** `urban_canyon`, `forest_dense`, `indoor_complex`, `open_field`

**Implementation:** `src/mili_vio/factor_graph/`, `embedded/src/vio/g2o_embedded.c`

### FR-3: Event-Driven Sharing

| Criterion | Target |
|--------|-----|
| Uncertainty threshold | 0.3 m |
| Bandwidth reduction | ≥ 70% |
| Sharing latency | < 20 ms |
| Group accuracy improvement | ≥ 40% |
| Maximum drones | 12 |

**Implementation:** `src/mili_vio/sharing/`, `embedded/src/sharing/sharing_embedded.c`

## 5. Acceptance Criteria

| Section | Automated test | Document |
|-----|------------|-----|
| FG vs EKF | `mili-vio-benchmark` | PHASE1_BENCHMARK.md |
| FR-1/2/3 SRS | `mili-vio-fr1/fr2/fr3 --validate-srs` | PHASE2/3 docs |
| Integrated E2E | `mili-vio-run` | integrated.yaml |
| Embedded 20 Hz | `mili_host_sim --quick` | PHASE5_EMBEDDED.md |
| Full validation | `mili-vio-validate` | PHASE6_VALIDATION.md |
| GPS-denied field | Manual | PHASE6 field checklist |
| Field group of 2–12 | Manual | PHASE6 field checklist |

## 6. Simulation Data Generation (legacy)

The initial CSV generation code from the old README has been moved into the package:

```bash
mili-vio-generate --output cooperative_vio_data.csv
```

The output includes scenarios, simulated FG vs EKF error, and SRS flags.

## 7. Innovation Compared to the EKF + Continuous Sharing Approach

1. **128-bit binary descriptor** (BNN) — not a float descriptor
2. **Factor graph** — not EKF as the main estimator
3. **Event-driven Landmark sharing** — not continuous raw position

---

*SRS document version: 1.0 — aligned with mili-vio `0.1.0`*
