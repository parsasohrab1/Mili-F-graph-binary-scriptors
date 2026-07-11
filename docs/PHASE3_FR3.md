# Phase 4 — FR-3: Event-Driven Cooperative Landmark Sharing

## Overview

| Component | Module |
|-----------|--------|
| UDP protocol | `sharing/protocol.py` |
| Compression (~20 B/lm) | `sharing/compression.py` |
| Bandwidth manager | `sharing/bandwidth.py` |
| Network simulator | `sharing/network.py` |
| Cooperative coordinator | `sharing/cooperative.py` |

## Message Format

```
Header (14 bytes):
  MAGIC(2) | VER(1) | TYPE(1) | DRONE_ID(1) | TIMESTAMP(4) |
  N_LM(1) | UNCERTAINTY(2) | SEQ(1) | CHECKSUM(1)

Landmark (20 bytes each) — NO raw position:
  LM_ID(2) | DESCRIPTOR(16) | UNCERT_Q(1) | FLAGS(1)
```

## Event Trigger

Sharing activates when `uncertainty > 0.3 m` (from FR-2 covariance).

## Usage

```bash
mili-vio-fr3 --drones 6 --steps 100
```

```python
from mili_vio.sharing import CooperativeCoordinator

drone = CooperativeCoordinator(drone_id=0)
result = drone.share_if_needed(uncertainty=0.5, landmarks=lms, timestamp_ns=ts)
received = drone.receive_and_integrate()  # → factor graph
```

## SRS Acceptance

| Metric | Target |
|--------|--------|
| Bandwidth reduction | ≥ 70% |
| Accuracy improvement | ≥ 40% |
| Sharing latency | < 20 ms |

Config: `configs/phase3_sharing.yaml`
