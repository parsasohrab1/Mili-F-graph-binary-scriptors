# API Integration Guide — Mili-VIO

Integration reference for flight-controller firmware, ground station, and third-party systems.

## Overview

```
┌─────────────┐   SPI    ┌──────────────┐   UART/SPI   ┌─────────────┐
│ BNN Product │◄────────►│ VIO MCU      │─────────────►│ Main FC     │
│ 1 (FR-1)    │          │ STM32H7      │  69-byte     │ STM32H7     │
└─────────────┘          │ FR-2 + FR-3   │  frame       └─────────────┘
                         └──────┬───────┘
                                │ UDP/UWB
                         ┌──────▼───────┐
                         │ Other drones │
                         └──────────────┘
```

| Layer | Language | Entry point |
|-------|----------|-------------|
| Desktop / CI | Python 3.10+ | `mili_vio` package + CLIs |
| Embedded VIO | C11 | `embedded/include/mili/` |
| FC consumer | C / Python | `fc_output.h` / `flight_controller.py` |

---

## Flight Controller Binary Frame

**Size:** 69 bytes, little-endian, XOR checksum on first 68 bytes.

### C structure

```c
// embedded/include/mili/fc_output.h
typedef struct {
    uint16_t magic;          // 0xFC01
    uint8_t  version;        // 1
    uint8_t  flags;          // bit0=valid, bit1=sharing, bit2=loop_closure
    uint64_t timestamp_us;
    float    position[3];    // x, y, z (m)
    float    orientation[3]; // roll, pitch, yaw (rad)
    float    uncertainty;
    float    covariance_diag[6];
    uint32_t opt_time_us;
    uint8_t  checksum;
} mili_fc_frame_t;
```

### Python pack / unpack

```python
from mili_vio.runtime.flight_controller import (
    FlightControllerOutput,
    pack_state_estimate,
    unpack_state_estimate,
)

frame: bytes = pack_state_estimate(output)   # len == 69
output = unpack_state_estimate(frame)
```

### Flags

| Bit | Name | Meaning |
|-----|------|---------|
| 0 | `FC_FLAG_VALID` | Pose estimate valid |
| 1 | `FC_FLAG_SHARING_ACTIVE` | FR-3 sharing triggered this cycle |
| 2 | `FC_FLAG_LOOP_CLOSURE` | Loop closure applied |

### C API

```c
#include "mili/fc_output.h"

uint8_t mili_fc_checksum(const uint8_t *data, uint32_t len);
int mili_fc_pack(const mili_fc_state_t *state, uint8_t *out, uint32_t out_len);
int mili_fc_unpack(const uint8_t *data, uint32_t len, mili_fc_state_t *state);
```

---

## Python Integrated Runtime

### High-level API

```python
from pathlib import Path
from mili_vio.runtime.integrated_pipeline import run_integrated

result = run_integrated(
    dataset_name="synthetic",      # or MH_01_easy, etc.
    dataset_root=Path("data/datasets"),
    num_frames=60,
    num_drones=1,
    drone_id=0,
)
# result.states — list of StateEstimate per frame
# result.fc_frames — list of bytes (69 B each)
```

### FlightControllerSink (callback)

```python
from mili_vio.runtime.flight_controller import FlightControllerSink

sink = FlightControllerSink()
sink.on_state(output)          # called each 20 Hz tick
latest = sink.latest_frame()   # bytes or None
```

### CLI

```bash
mili-vio-run --dataset synthetic --frames 60 --drones 2 --verify-alignment
```

| Flag | Description |
|------|-------------|
| `--dataset` | `synthetic`, EuRoC, or TUM-VI sequence name |
| `--dataset-root` | Root with `euroc/` and `tum_vi/` folders |
| `--frames` | Max frames to process |
| `--drones` | Multi-drone integrated simulation |
| `--verify-alignment` | Cross-check Python vs embedded SRS constants |

---

## FR-1 — BNN Descriptor (SPI)

### Python

```python
from mili_vio.descriptors.bnn.api import BNNDescriptorAPI

api = BNNDescriptorAPI(transport="simulated")  # or "serial", "spidev", "udp"
desc = api.extract(image_gray_uint8)  # 640×480
# desc.bits — 128-bit descriptor
# desc.chip_time_us, desc.energy_uj
```

### SPI wire protocol

Header 8 bytes (`embedded/include/mili/drivers/bnn_protocol.h`):

| Offset | Field |
|--------|-------|
| 0–1 | magic `0xB1B1` |
| 2 | cmd (`0x10` = EXTRACT) |
| 3–4 | payload_len |
| 5 | sequence |
| 6 | flags |
| 7 | checksum |

CLI validation: `mili-vio-fr1 --validate-srs --transport serial --port COM3`

---

## FR-2 — Factor Graph State

### Python estimator

```python
from mili_vio.factor_graph.estimator import FR2FactorGraphEstimator
from mili_vio.vio.datasets.synthetic import generate_synthetic

estimator = FR2FactorGraphEstimator()
dataset = generate_synthetic(num_frames=60)
result = estimator.run_on_dataset(dataset, scenario="open_field")
# result.mean_position_error_m, result.loop_closures, ...
```

### Embedded

```c
#include "mili/vio/factor_graph.h"

mili_factor_graph_t *fg = mili_fg_create();
mili_fg_add_pose(fg, &pose);
mili_fg_add_imu(fg, pose_i, pose_j, &preint);
mili_fg_optimize(fg);  // g2o_embedded Gauss-Newton
```

SRS limits: `MILI_FG_MEMORY_BUDGET` (2 MB), `MILI_FG_MAX_OPT_MS` (5 ms).

---

## FR-3 — Cooperative Sharing

### Python network

```python
from mili_vio.sharing.cooperative import MultiDroneSimulator
from mili_vio.sharing.transport import create_network_transport
from mili_vio.sharing.network import NetworkConfig

net = create_network_transport("udp", NetworkConfig(base_port=7700, max_drones=12))
sim = MultiDroneSimulator(num_drones=6, network=net)
metrics = sim.run()
```

### UDP payload

Sharing uses compressed landmarks (~20 B each) when local uncertainty > `MILI_UNCERTAINTY_THRESHOLD` (0.3 m).

Embedded: `mili_share_send_uwb()` / `comm_udp_host.c` on desktop sim.

CLI: `mili-vio-fr3 --validate-srs --drones 6 --transport udp`

---

## SRS Constants (Python ↔ Embedded)

Single source of truth alignment:

| Constant | Python | Embedded |
|----------|--------|----------|
| State rate | `SRSConstants.STATE_UPDATE_HZ` | `MILI_STATE_UPDATE_HZ` |
| FG memory | `SRSConstants.FG_MEMORY_BUDGET` | `MILI_FG_MEMORY_BUDGET` |
| Max drones | `SRSConstants.MAX_DRONES` | `MILI_MAX_DRONES` |
| Descriptor bits | `SRSConstants.DESCRIPTOR_BITS` | `MILI_DESCRIPTOR_BITS` |

```python
from mili_vio.common.srs_constants import SRSConstants
from mili_vio.runtime.integrated_pipeline import verify_embedded_alignment

verify_embedded_alignment()  # raises if mismatch
```

---

## Configuration Files

| File | Scope |
|------|-------|
| `configs/phase1.yaml` | VIO benchmark, camera intrinsics, datasets |
| `configs/phase2.yaml` | FR-2 sliding window, 4 scenarios |
| `configs/phase3_sharing.yaml` | FR-3 network, acceptance |
| `configs/integrated.yaml` | E2E runtime |
| `configs/phase5_embedded.yaml` | Embedded targets |
| `configs/phase6_validation.yaml` | Acceptance orchestrator |

---

## Validation Entry Points

```bash
mili-vio-validate --quick              # Phase 6 report YAML
mili-vio-benchmark --dataset synthetic # FG vs EKF JSON
mili-vio-fr2 --validate-srs          # FR-2 per-scenario YAML
mili-vio-fr3 --validate-srs --12-drones
embedded/scripts/build.ps1 -Quick -Test
```

Report output: `data/benchmarks/phase6/phase6_validation_report.yaml`

---

## Versioning

Package version: `pyproject.toml` → `version = "0.1.0"`.

Release process: [RELEASE.md](RELEASE.md).

When integrating, pin to a git tag (e.g. `v0.1.0`) once published.
