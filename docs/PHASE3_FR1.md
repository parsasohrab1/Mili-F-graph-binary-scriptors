# Phase 3 — FR-1: BNN Binary Descriptor Extraction

## Overview

Complete FR-1 implementation with BNN hardware integration (Product 1):

| Component | Module |
|-----------|--------|
| SPI protocol | `descriptors/bnn/protocol.py` |
| SPI/DMA driver | `descriptors/bnn/driver.py` |
| Extraction API | `descriptors/bnn/api.py` |
| ORB/BRIEF fallback | `descriptors/fallback.py` |
| Optimized matching | `descriptors/matching.py` |
| Benchmark | `descriptors/benchmark.py` |

## SPI Protocol

```
Frame: [MAGIC 2B][CMD 1B][LEN 2B][SEQ 1B][FLAGS 1B][CSUM 1B][PAYLOAD]

Commands:
  0x10 EXTRACT_DESCRIPTORS  — image in, keypoints+128-bit desc out
  0x01 RESET
  0x12 GET_VERSION
```

## Usage

```bash
# BNN extraction benchmark
mili-vio-fr1 --frames 10

# Force software fallback (ORB)
mili-vio-fr1 --fallback --frames 10
```

```python
from mili_vio.descriptors import BNNDescriptorAPI

api = BNNDescriptorAPI()
result = api.extract(image_gray)  # max 200 keypoints, 128-bit each
print(result.extraction_time_ms, result.energy_mj)

repeatability = api.measure_repeatability(frame_a, frame_b)
```

## SRS Acceptance Criteria

| Metric | Target | Config |
|--------|--------|--------|
| Extraction time | < 2 ms | `phase3.acceptance.extraction_time_ms` |
| Repeatability | > 90% | `phase3.acceptance.repeatability_pct` |
| Energy | < 5 mJ/frame | `phase3.acceptance.energy_mj_per_frame` |

## Fallback

When BNN is unavailable, `SoftwareFallbackExtractor` uses ORB/BRIEF automatically.
Set `phase3.fallback.auto_select: true` in `configs/phase3.yaml`.

## Embedded Integration (STM32H7)

Replace `SimulatedBNNDriver` with HAL SPI+DMA calls in `SPIDMADriver._spi_transfer()`.
