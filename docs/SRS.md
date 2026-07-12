# SRS — سامانه ناوبری مشارکتی Mili-VIO (Product 2)

> سند الزامات نرم‌افزاری (SRS). برای راه‌اندازی عملیاتی [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md) و برای API یکپارچه‌سازی [API_INTEGRATION.md](API_INTEGRATION.md) را ببینید.

## ۱. مقدمه

### ۱.۱ هدف

سامانه ناوبری مشارکتی برای گروه پهپادها با Factor-Graph، توصیفگر باینری (BNN Product 1)، و اشتراک رویداد-محور در محیط GPS-denied.

### ۱.۲ محدوده

- VIO مستقل از GPS (دوربین + IMU)
- همکاری ۲–۱۲ پهپاد
- خطای موقعیت هدف: **< ۰.۵ m** (شرایط عادی)
- نرخ به‌روزرسانی حالت: **۲۰ Hz**

### ۱.۳ اصطلاحات

| اختصار | معنی |
|--------|------|
| VIO | Visual-Inertial Odometry |
| FG | Factor Graph |
| EKF | Extended Kalman Filter |
| BNN | Binary Neural Network (Product 1) |

## ۲. معماری

```
گروه پهپاد (≤12) ──► اشتراک Landmark رویداد-محور
       │
       ▼
  VIO MCU (STM32H7): Camera → BNN → FG → Sharing → FC frame (69 B)
```

## ۳. الزامات سخت‌افزاری

| مؤلفه | مشخصات |
|--------|--------|
| MCU | STM32H7, 480 MHz |
| دوربین | Global shutter 640×480 @ 30 fps |
| IMU | Bosch BMI088 |
| RAM FG | ≤ 2 MB |
| ارتباط | UWB / Wi-Fi, تأخیر < 50 ms |

## ۴. الزامات عملکردی

### FR-1: توصیفگر باینری

| معیار | هدف |
|--------|-----|
| زمان استخراج | < 2 ms |
| تکرارپذیری | > 90% |
| انرژی | < 5 mJ/frame |
| خروجی | 128-bit × ≤200 keypoint |

**پیاده‌سازی:** `src/mili_vio/descriptors/bnn/`, `embedded/src/drivers/bnn_spi.c`

### FR-2: گراف فاکتور

| معیار | هدف |
|--------|-----|
| خطای موقعیت | < 0.5 m |
| خطای جهت | < 2° |
| زمان بهینه‌سازی | < 5 ms |
| حافظه | ≤ 2 MB |
| Loop closure | فعال |

**سناریوهای SRS:** `urban_canyon`, `forest_dense`, `indoor_complex`, `open_field`

**پیاده‌سازی:** `src/mili_vio/factor_graph/`, `embedded/src/vio/g2o_embedded.c`

### FR-3: اشتراک رویداد-محور

| معیار | هدف |
|--------|-----|
| آستانه عدم‌قطعیت | 0.3 m |
| کاهش پهنای‌باند | ≥ 70% |
| تأخیر اشتراک | < 20 ms |
| بهبود دقت گروهی | ≥ 40% |
| حداکثر پهپاد | 12 |

**پیاده‌سازی:** `src/mili_vio/sharing/`, `embedded/src/sharing/sharing_embedded.c`

## ۵. معیارهای پذیرش (Acceptance)

| بخش | تست خودکار | سند |
|-----|------------|-----|
| FG vs EKF | `mili-vio-benchmark` | PHASE1_BENCHMARK.md |
| FR-1/2/3 SRS | `mili-vio-fr1/fr2/fr3 --validate-srs` | PHASE2/3 docs |
| یکپارچه E2E | `mili-vio-run` | integrated.yaml |
| Embedded 20 Hz | `mili_host_sim --quick` | PHASE5_EMBEDDED.md |
| Validation کامل | `mili-vio-validate` | PHASE6_VALIDATION.md |
| میدان GPS-denied | دستی | PHASE6 field checklist |
| گروه ۲–۱۲ میدانی | دستی | PHASE6 field checklist |

## ۶. تولید داده شبیه‌سازی (legacy)

کد اولیه تولید CSV در README قدیمی به پکیج منتقل شده:

```bash
mili-vio-generate --output cooperative_vio_data.csv
```

خروجی شامل سناریوها، خطای FG vs EKF شبیه‌سازی‌شده، و پرچم‌های SRS است.

## ۷. نوآوری نسبت به رویکرد EKF + اشتراک پیوسته

1. **توصیفگر باینری ۱۲۸-bit** (BNN) — نه float descriptor
2. **Factor-graph** — نه EKF به‌عنوان estimator اصلی
3. **اشتراک Landmark رویداد-محور** — نه موقعیت خام پیوسته

---

*نسخه سند SRS: 1.0 — هم‌تراز با mili-vio `0.1.0`*
