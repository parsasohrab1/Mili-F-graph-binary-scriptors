# راهنمای اپراتور — Mili-VIO

راهنمای نصب، کالیبراسیون، و استقرار firmware برای تیم میدانی و آزمایشگاه.

## ۱. پیش‌نیازها

### نرم‌افزار (میز توسعه)

| ابزار | نسخه | کاربرد |
|--------|------|--------|
| Python | ≥ 3.10 | الگوریتم‌ها، validation، log analysis |
| pip | جدید | `pip install -e ".[dev,vio]"` |
| CMake | ≥ 3.16 | build embedded host sim / firmware |
| Git | — | clone و CI |
| OpenOCD یا ST-Link Utility | — | فلش STM32H7 |

### سخت‌افزار (هر پهپاد)

| مؤلفه | مشخصات |
|--------|--------|
| MCU VIO | STM32H7 @ 480 MHz |
| دوربین | Global shutter 640×480 @ 30 fps (DCMI) |
| IMU | Bosch BMI088 (SPI) |
| BNN | Product 1 — توصیفگر باینری 128-bit |
| ارتباط گروهی | UWB یا Wi-Fi (UDP) |
| FC اصلی | STM32H7 — دریافت pose از VIO board |

## ۲. نصب — میز توسعه

```bash
git clone <repository-url>
cd Mili-F-graph-binary-scriptors
pip install -e ".[dev,vio]"
```

تأیید نصب:

```bash
mili-vio-run --dataset synthetic --frames 10
mili-vio-validate --quick --skip-embedded
```

### Windows (embedded sim)

```powershell
embedded\scripts\build.ps1 -Quick -Test
```

خروجی موفق: `State update rate: 20.0 Hz … ALL PASS`

## ۳. کالیبراسیون

### ۳.۱ دوربین (intrinsics)

فایل پیکربندی: `configs/phase1.yaml` → `phase1.camera`

| پارامتر | EuRoC پیش‌فرض | توضیح |
|---------|---------------|--------|
| `fx`, `fy` | 458.654 / 457.296 | focal length (px) |
| `cx`, `cy` | 367.215 / 248.375 | principal point |
| `baseline` | 0.11 m | برای stereo (اختیاری) |

**روش کالیبراسیون:**

1. چاپ checkerboard 9×6 (یا 8×6) با اندازه مربع مشخص (مثلاً 25 mm)
2. ضبط ۲۰+ تصویر از زوایای مختلف
3. اجرای کالیبراسیون OpenCV (`cv2.calibrateCamera`) یا ابزار Kalibr
4. مقادیر `fx, fy, cx, cy` را در `phase1.yaml` و `embedded` camera config به‌روز کنید

برای TUM-VI از `camchain.yaml` همان sequence استفاده کنید.

### ۳.۲ IMU (BMI088)

| پارامتر | مقدار SRS | فایل |
|---------|----------|------|
| نرخ نمونه‌برداری | 200 Hz | `mili_config.h` → `MILI_IMU_SAMPLE_HZ` |
| محورها | accel + gyro | `embedded/src/hal/bmi088_hal.c` |

**کالیبراسیون IMU:**

1. **ساکن:** ۶۰ ثانیه ثابت روی سطح افقی → تخمین bias ژیروسکوپ و شتاب‌سنج
2. **مقیاس:** مقایسه با مرجع (اگر IMU مرجع دارید) یا factory trim در رجیستر BMI088
3. biasها را در `imu_preintegration` / embedded IMU driver ذخیره کنید

### ۳.۳ هم‌زمان‌سازی دوربین–IMU (time sync)

- تایم‌استمپ DCMI frame و SPI IMU باید در یک ساعت monotonic (µs) باشند
- روی STM32: TIM + DWT (`embedded/src/hal/dwt.c`)
- تأخیر ثابت camera–IMU را با حرکت تند پهپاد اندازه بگیرید و offset را در firmware اعمال کنید

### ۳.۴ شبکه گروهی (۲–۱۲ پهپاد)

`configs/phase3_sharing.yaml`:

| پارامتر | پیش‌فرض |
|---------|---------|
| `base_port` | 7700 |
| `max_drones` | 12 |
| `drone_id` | 0 … 11 (یکتا per aircraft) |

هر پهپاد: `drone_id` یکتا + IP/port در همان subnet. برای UWB از `comm_uwb.c` AT init استفاده کنید.

## ۴. فلش Firmware (STM32H7)

### ۴.۱ Build

```bash
cd embedded
cmake -B build -DMILI_HOST_SIM=OFF
cmake --build build --config Release
```

خروجی: `build/mili_firmware` (یا `.elf`)

### ۴.۲ فلش با OpenOCD

```bash
openocd -f interface/stlink.cfg -f target/stm32h7x.cfg \
  -c "program build/mili_firmware.elf verify reset exit"
```

### ۴.۳ فلش با STM32CubeProgrammer (Windows)

1. ST-Link را به SWD وصل کنید
2. Connect → Load `mili_firmware.elf` → Start Programming
3. Verify + Reset

### ۴.۴ پس از فلش — smoke test

1. UART debug را به 115200 baud وصل کنید
2. باید log init دوربین / IMU / BNN SPI دیده شود
3. `mili_acceptance_print` پس از ۳۰ ثانیه: 20 Hz PASS

```bash
# روی host قبل از میدان
embedded/build/Release/mili_host_sim.exe --quick
```

## ۵. اتصال به Flight Controller

VIO board pose را در قالب **69 بایت** به FC اصلی می‌فرستد (UART یا SPI).

| فیلد | نوع | واحد |
|------|-----|------|
| position | float×3 | m |
| orientation | float×3 | rad (roll, pitch, yaw) |
| uncertainty | float | m |
| covariance_diag | float×6 | diag pose covariance |

جزئیات wire format: [API_INTEGRATION.md](API_INTEGRATION.md#flight-controller-binary-frame)

## ۶. چک‌لیست قبل از پرواز

- [ ] `mili-vio-validate --quick` PASS روی میز توسعه
- [ ] کالیبراسیون دوربین/IMU به‌روز (< ۳۰ روز)
- [ ] `drone_id` یکتا در گروه
- [ ] BNN Product 1 پاسخ SPI (`mili-vio-fr1 --ping --transport serial`)
- [ ] FC frame checksum روی loopback UART تأیید شده
- [ ] تست ۳۰ ثانیه‌ای embedded روی سخت‌افزار: 20 Hz، بدون crash

## ۷. عیب‌یابی

| علامت | احتمال | اقدام |
|--------|--------|--------|
| نرخ < 20 Hz | FG سنگین / CPU | profiler stage overruns را ببینید |
| BNN timeout | SPI wiring / clock | `MILI_BNN_SPI_CLOCK_HZ` را کاهش دهید |
| اشتراک کار نمی‌کند | firewall / port | `mili-vio-fr3 --transport udp` تست |
| drift زیاد | کالیبراسیون | IMU bias + camera intrinsics |
| FC checksum fail | endianness | `fc_output.h` ↔ Python `pack_state_estimate` |

## ۸. مراجع

- [API_INTEGRATION.md](API_INTEGRATION.md) — پروتکل‌ها و API
- [PHASE5_EMBEDDED.md](PHASE5_EMBEDDED.md) — معماری firmware
- [PHASE6_VALIDATION.md](PHASE6_VALIDATION.md) — پذیرش SRS و تست میدانی
