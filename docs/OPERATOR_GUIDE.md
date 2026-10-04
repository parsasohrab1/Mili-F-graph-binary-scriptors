# Operator Guide — Mili-VIO

Installation, calibration, and firmware deployment guide for field and lab teams.

## 1. Prerequisites

### Software (development desk)

| Tool | Version | Purpose |
|--------|------|--------|
| Python | ≥ 3.10 | Algorithms, validation, log analysis |
| pip | latest | `pip install -e ".[dev,vio]"` |
| CMake | ≥ 3.16 | build embedded host sim / firmware |
| Git | — | Clone and CI |
| OpenOCD or ST-Link Utility | — | Flashing STM32H7 |

### Hardware (per drone)

| Component | Specification |
|--------|--------|
| MCU VIO | STM32H7 @ 480 MHz |
| Camera | Global shutter 640×480 @ 30 fps (DCMI) |
| IMU | Bosch BMI088 (SPI) |
| BNN | Product 1 — 128-bit binary descriptor |
| Group communication | UWB or Wi-Fi (UDP) |
| Main FC | STM32H7 — receives pose from VIO board |

## 2. Installation — Development Desk

```bash
git clone <repository-url>
cd Mili-F-graph-binary-scriptors
pip install -e ".[dev,vio]"
```

Verify installation:

```bash
mili-vio-run --dataset synthetic --frames 10
mili-vio-validate --quick --skip-embedded
```

### Windows (embedded sim)

```powershell
embedded\scripts\build.ps1 -Quick -Test
```

Successful output: `State update rate: 20.0 Hz … ALL PASS`

## 3. Calibration

### 3.1 Camera (intrinsics)

Configuration file: `configs/phase1.yaml` → `phase1.camera`

| Parameter | EuRoC default | Description |
|---------|---------------|--------|
| `fx`, `fy` | 458.654 / 457.296 | focal length (px) |
| `cx`, `cy` | 367.215 / 248.375 | principal point |
| `baseline` | 0.11 m | For stereo (optional) |

**Calibration procedure:**

1. Print a 9×6 (or 8×6) checkerboard with a known square size (e.g., 25 mm)
2. Capture 20+ images from different angles
3. Run OpenCV calibration (`cv2.calibrateCamera`) or the Kalibr tool
4. Update the `fx, fy, cx, cy` values in `phase1.yaml` and the `embedded` camera config

For TUM-VI, use the `camchain.yaml` of the same sequence.

### 3.2 IMU (BMI088)

| Parameter | SRS value | File |
|---------|----------|------|
| Sampling rate | 200 Hz | `mili_config.h` → `MILI_IMU_SAMPLE_HZ` |
| Axes | accel + gyro | `embedded/src/hal/bmi088_hal.c` |

**IMU calibration:**

1. **Static:** keep still for 60 seconds on a level surface → estimate gyroscope and accelerometer bias
2. **Scale:** compare against a reference (if you have a reference IMU) or use the factory trim in the BMI088 register
3. Store the biases in `imu_preintegration` / the embedded IMU driver

### 3.3 Camera–IMU Time Synchronization

- The DCMI frame and SPI IMU timestamps must be on the same monotonic clock (µs)
- On STM32: TIM + DWT (`embedded/src/hal/dwt.c`)
- Measure the fixed camera–IMU delay with sharp drone motion and apply the offset in firmware

### 3.4 Group Network (2–12 drones)

`configs/phase3_sharing.yaml`:

| Parameter | Default |
|---------|---------|
| `base_port` | 7700 |
| `max_drones` | 12 |
| `drone_id` | 0 … 11 (unique per aircraft) |

Each drone: unique `drone_id` + IP/port on the same subnet. For UWB, use the `comm_uwb.c` AT init.

## 4. Flashing Firmware (STM32H7)

### 4.1 Build

```bash
cd embedded
cmake -B build -DMILI_HOST_SIM=OFF
cmake --build build --config Release
```

Output: `build/mili_firmware` (or `.elf`)

### 4.2 Flashing with OpenOCD

```bash
openocd -f interface/stlink.cfg -f target/stm32h7x.cfg \
  -c "program build/mili_firmware.elf verify reset exit"
```

### 4.3 Flashing with STM32CubeProgrammer (Windows)

1. Connect the ST-Link to SWD
2. Connect → Load `mili_firmware.elf` → Start Programming
3. Verify + Reset

### 4.4 After Flashing — Smoke Test

1. Connect the UART debug at 115200 baud
2. The camera / IMU / BNN SPI init log should be visible
3. `mili_acceptance_print` after 30 seconds: 20 Hz PASS

```bash
# On the host before going to the field
embedded/build/Release/mili_host_sim.exe --quick
```

## 5. Connection to the Flight Controller

The VIO board sends the pose to the main FC in a **69-byte** format (UART or SPI).

| Field | Type | Unit |
|------|-----|------|
| position | float×3 | m |
| orientation | float×3 | rad (roll, pitch, yaw) |
| uncertainty | float | m |
| covariance_diag | float×6 | diag pose covariance |

Wire format details: [API_INTEGRATION.md](API_INTEGRATION.md#flight-controller-binary-frame)

## 6. Pre-Flight Checklist

- [ ] `mili-vio-validate --quick` PASS on the development desk
- [ ] Camera/IMU calibration up to date (< 30 days)
- [ ] Unique `drone_id` in the group
- [ ] BNN Product 1 responds over SPI (`mili-vio-fr1 --ping --transport serial`)
- [ ] FC frame checksum verified on UART loopback
- [ ] 30-second embedded test on hardware: 20 Hz, no crash

## 7. Troubleshooting

| Symptom | Likely cause | Action |
|--------|--------|--------|
| Rate < 20 Hz | Heavy FG / CPU | See the profiler stage overruns |
| BNN timeout | SPI wiring / clock | Reduce `MILI_BNN_SPI_CLOCK_HZ` |
| Sharing does not work | Firewall / port | Test with `mili-vio-fr3 --transport udp` |
| Large drift | Calibration | IMU bias + camera intrinsics |
| FC checksum fail | endianness | `fc_output.h` ↔ Python `pack_state_estimate` |

## 8. References

- [API_INTEGRATION.md](API_INTEGRATION.md) — Protocols and API
- [PHASE5_EMBEDDED.md](PHASE5_EMBEDDED.md) — Firmware architecture
- [PHASE6_VALIDATION.md](PHASE6_VALIDATION.md) — SRS acceptance and field testing
