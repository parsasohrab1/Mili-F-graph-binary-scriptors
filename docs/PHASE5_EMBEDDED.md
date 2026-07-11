# Phase 5 — Embedded Firmware (STM32H7)

## Overview

| Component | Path |
|-----------|------|
| Config | `include/mili/mili_config.h` |
| Camera DCMI | `src/drivers/camera_dcmi.c` |
| IMU BMI088 | `src/drivers/imu_bmi088.c` |
| BNN SPI/DMA | `src/drivers/bnn_spi.c` |
| UWB / Wi-Fi | `src/drivers/comm_uwb.c`, `comm_wifi.c` |
| Factor graph | `src/vio/factor_graph.c` |
| g2o stub | `src/vio/g2o_embedded.c` |
| Sharing | `src/sharing/sharing_embedded.c` |
| Pipeline 20Hz | `src/pipeline/pipeline.c` |
| FreeRTOS tasks | `src/rtos/tasks.c` |

## Task Scheduling

```
Priority 5: camera_task  (30 fps)
Priority 4: bnn_task      (descriptor extraction)
Priority 3: vio_task      (20 Hz factor graph)
Priority 2: sharing_task  (event-driven UDP/UWB)
Priority 1: profiler_task (1 Hz metrics)
```

## Build — Host Simulation

```bash
cd embedded
cmake -B build -DMILI_HOST_SIM=ON
cmake --build build
ctest --test-dir build
./build/mili_host_sim 10   # 10 second acceptance run
```

## Build — STM32H7 Firmware

```bash
cmake -B build -DMILI_HOST_SIM=OFF
cmake --build build
# Flash build/mili_firmware via OpenOCD/ST-Link
```

Link with: FreeRTOS, STM32 HAL, g2o_embedded (or GTSAM embedded).

## SRS Acceptance

| Metric | Target |
|--------|--------|
| State update rate | 20 Hz stable |
| Factor graph RAM | ≤ 2 MB |
| Stability | > 1 hour no crash |

Config: `configs/phase5_embedded.yaml`

## Integration Checklist

- [ ] Replace `mili_camera_sim_fill` with DCMI DMA callback
- [ ] Replace `mili_bnn_extract` sim with SPI+DMA to Product 1
- [ ] Link `g2o_embedded` in `mili_fg_optimize()`
- [ ] Configure UWB module AT commands in `mili_uwb_init()`
- [ ] Enable DWT cycle counter in `prof_now_us()`
