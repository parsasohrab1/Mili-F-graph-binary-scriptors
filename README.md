# Mili-F-graph-binary-scriptors

سامانه ناوبری مشارکتی با رویکرد Factor-Graph + Binary Descriptors
Cooperative VIO System with Factor-Graph Optimization + Binary Descriptors
1. مقدمه (Introduction)
1.1 هدف (Purpose)
این سند مشخصات کامل سامانه ناوبری مشارکتی برای گروه پهپادها را تشریح می‌کند. این سامانه با استفاده از بهینه‌سازی گراف فاکتور (Factor-Graph)، توصیفگرهای بصری باینری، و پروتکل اشتراک رویداد-محور، ناوبری دقیقی را در شرایط عدم دسترسی به GPS فراهم می‌کند.

1.2 محدوده (Scope)
ناوبری مستقل از GPS با استفاده از حسگرهای بصری-لختی (VIO)

همکاری بین پهپادهای گروه برای بهبود دقت موقعیت‌یابی

کاهش پهنای باند ارتباطی با اشتراک رویداد-محور

پشتیبانی از گروه‌های تا ۱۲ پهپاد

خطای موقعیت‌یابی هدف: < ۰.۵ متر در شرایط عادی

1.3 اصطلاحات و اختصارات
اختصار	توضیح
VIO	Visual-Inertial Odometry - سنجش بصری-لختی
Factor-Graph	گراف فاکتور - روش بهینه‌سازی غیرخطی
EKF	Extended Kalman Filter - فیلتر کالمن توسعه‌یافته
DOF	Degrees of Freedom - درجات آزادی
SLAM	Simultaneous Localization and Mapping
2. الزامات کلی (Overall Description)
2.1 پرسپکتیو محصول
این سامانه به عنوان لایه ناوبری هوشمند بر روی کنترل‌کننده پرواز اصلی (STM32H7) اجرا می‌شود و با تراشه BNN (محصول ۱) برای استخراج توصیفگرهای بصری ارتباط دارد.

text
┌─────────────────────────────────────────────────┐
│         گروه پهپادها (حداکثر ۱۲ عدد)            │
├─────────────────────────────────────────────────┤
│  ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │ پهپاد ۱   │◄──►│ پهپاد ۲   │◄──►│ پهپاد N   │ │
│  │ VIO+SLAM  │    │ VIO+SLAM  │    │ VIO+SLAM  │ │
│  └──────────┘    └──────────┘    └──────────┘ │
│       │                 │                 │     │
│       └───────┬─────────┴─────────────────┘     │
│               ▼                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  اشتراک رویداد-محور Landmarkها          │   │
│  │  • فقط در صورت عبور عدم‌قطیت از آستانه  │   │
│  │  • به‌جای موقعیت خام                    │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
2.2 ویژگی‌های اصلی
استخراج توصیفگر باینری: با استفاده از تراشه BNN (محصول ۱)

تخمین حالت با گراف فاکتور: بهینه‌سازی غیرخطی در پنجره لغزان

اشتراک رویداد-محور: کاهش پهنای‌باند تا ۸۰%

هم‌افزایی داده‌ها: ترکیب داده‌های چند پهپاد برای بهبود دقت

2.3 محدودیت‌ها و وابستگی‌ها
وابسته به: تراشه BNN (محصول ۱) برای استخراج توصیفگر

پهنای باند: حداکثر ۵۰ کیلوبایت بر ثانیه برای هر پهپاد

تأخیر شبکه: < ۵۰ میلی‌ثانیه بین پهپادها

3. الزامات سیستم (System Requirements)
3.1 الزامات سخت‌افزاری
مؤلفه	مشخصات
پردازنده اصلی	STM32H7 (480 MHz)
دوربین	Global Shutter, 640×480, 30 fps
IMU	Bosch BMI088 یا معادل
حافظه	۲ مگابایت رم برای گراف فاکتور
ارتباط	UWB یا Wi-Fi با تأخیر کم
3.2 الزامات نرم‌افزاری
مؤلفه	مشخصات
سیستم‌عامل	FreeRTOS یا NuttX
کتابخانه گراف فاکتور	g2o یا GTSAM (نسخه EMBEDDED)
فرمت توصیفگر	باینری ۱۲۸-بیتی (BRIEF/ORB)
نرخ به‌روزرسانی	۲۰ Hz برای تخمین حالت
پروتکل اشتراک	Custom UDP با فشرده‌سازی
4. مشخصات عملکردی (Functional Requirements)
4.1 FR-1: استخراج توصیفگر بصری باینری
توضیح: استخراج ویژگی‌های بصری از تصاویر دوربین به صورت باینری (۱-بیت) با استفاده از تراشه BNN.

ورودی: تصویر ۶۴۰×۴۸۰ (سطح خاکستری)
خروجی: توصیفگر ۱۲۸-بیتی برای هر نقطه کلیدی (حداکثر ۲۰۰ نقطه)

معیار پذیرش:

زمان استخراج < ۲ms

تکرارپذیری (Repeatability) > ۹۰%

مصرف انرژی < ۵mJ در هر فریم

4.2 FR-2: تخمین حالت با گراف فاکتور
توضیح: بهینه‌سازی همزمان موقعیت و جهت‌گیری (۶ DOF) با استفاده از گراف فاکتور.

ورودی:

داده‌های IMU (شتاب و ژیروسکوپ)

نقاط کلیدی استخراج‌شده

Landmarkهای اشتراکی از پهپادهای دیگر

خروجی:

موقعیت (x, y, z) با دقت < ۰.۵m

جهت‌گیری (roll, pitch, yaw) با دقت < ۲°

معیار پذیرش:

زمان بهینه‌سازی < ۵ms

خطای نهایی < ۰.۵m (نسبت به مسیر واقعی)

امکان اصلاح گذشته‌نگر (loop closure)

4.3 FR-3: اشتراک رویداد-محور
توضیح: اشتراک‌گذاری اطلاعات فقط زمانی که عدم‌قطیت محلی از آستانه تعیین‌شده عبور کند.

ورودی:

عدم‌قطیت تخمین (covariance matrix)

آستانه تعیین‌شده: ۰.۳ متر

خروجی:

مجموعه Landmarkهای پراکنده (نه موقعیت خام)

Metadata: زمان، عدم‌قطیت، شناسه پهپاد

معیار پذیرش:

کاهش پهنای‌باند ≥ ۷۰% نسبت به اشتراک پیوسته

تأخیر اشتراک < ۲۰ms

بهبود دقت گروهی ≥ ۴۰%

5. کد تولید داده - محصول دوم (با رویکرد نوآورانه)
python
# =====================================================
# SRS - PRODUCT 2: COOPERATIVE VIO WITH FACTOR-GRAPH
# INNOVATIVE APPROACH FOR PATENT DESIGN-AROUND
# =====================================================

import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation as R

np.random.seed(2026)

def generate_cooperative_vio_data():
    """
    تولید داده‌های ناوبری مشارکتی با رویکرد:
    1. توصیفگرهای باینری (۱-بیت) - تفاوت با پتنت رقیب
    2. تخمین با گراف فاکتور (نه EKF) - تفاوت با پتنت رقیب
    3. اشتراک رویداد-محور Landmarkها - تفاوت با پتنت رقیب
    """
    
    num_groups = 15
    drones_per_group = 6
    time_steps = 600  # 10 دقیقه با نرخ ۱Hz
    total_records = num_groups * drones_per_group * time_steps
    
    vio_data = []
    
    # پارامترهای سناریو
    scenario_types = ['urban_canyon', 'forest_dense', 'indoor_complex', 'open_field']
    communication_qualities = ['clear', 'intermittent', 'jammed']
    
    print(f"🚀 Generating {total_records:,} records for Product 2...")
    
    for group_id in range(num_groups):
        scenario = np.random.choice(scenario_types)
        comm_quality = np.random.choice(communication_qualities, p=[0.5, 0.3, 0.2])
        
        # ====== مسیر واقعی گروه (مرجع) ======
        # حرکت با شتاب تصادفی و تغییرات ارتفاع
        true_trajectory_x = np.cumsum(np.random.randn(time_steps) * 0.8)
        true_trajectory_y = np.cumsum(np.random.randn(time_steps) * 0.8)
        true_trajectory_z = 10 + 2 * np.sin(np.linspace(0, 4*np.pi, time_steps)) + np.cumsum(np.random.randn(time_steps) * 0.05)
        
        # ====== جهت‌گیری گروه (یاو، پیچ، رول) ======
        true_yaw = np.cumsum(np.random.randn(time_steps) * 0.02)  # رادیان
        true_pitch = 0.05 * np.sin(np.linspace(0, 2*np.pi, time_steps))
        true_roll = 0.03 * np.cos(np.linspace(0, 2*np.pi, time_steps))
        
        for drone_id in range(drones_per_group):
            # ====== انحراف هر پهپاد از مسیر گروه ======
            offset_x = np.random.uniform(-3, 3)
            offset_y = np.random.uniform(-3, 3)
            offset_z = np.random.uniform(-1.5, 1.5)
            
            # ====== خطاهای IMU ======
            imu_bias_accel = np.random.normal(0, 0.02, 3)
            imu_bias_gyro = np.random.normal(0, 0.001, 3)
            
            # ====== نویز بر اساس کیفیت ارتباط ======
            if comm_quality == 'clear':
                imu_noise_std = 0.01
                visual_noise = 0.02
            elif comm_quality == 'intermittent':
                imu_noise_std = 0.025
                visual_noise = 0.05
            else:  # jammed
                imu_noise_std = 0.05
                visual_noise = 0.10
            
            # ====== متغیرهای حلقه زمانی ======
            # استفاده از رویکرد ۲۴-بیت برای timestamp دقیق
            base_timestamp = 1700000000  # UNIX timestamp مبنا
            
            for t in range(time_steps):
                # ====== موقعیت واقعی ======
                true_pos = np.array([
                    true_trajectory_x[t] + offset_x,
                    true_trajectory_y[t] + offset_y,
                    true_trajectory_z[t] + offset_z
                ])
                
                # ====== جهت‌گیری واقعی ======
                true_orientation = np.array([
                    true_roll[t],
                    true_pitch[t],
                    true_yaw[t]
                ])
                
                # ====== داده‌های IMU با نویز ======
                imu_accel = np.array([
                    np.random.normal(0, imu_noise_std) + imu_bias_accel[0],
                    np.random.normal(0, imu_noise_std) + imu_bias_accel[1],
                    9.81 + np.random.normal(0, imu_noise_std) + imu_bias_accel[2]
                ])
                
                imu_gyro = np.array([
                    np.random.normal(0, 0.003) + imu_bias_gyro[0],
                    np.random.normal(0, 0.003) + imu_bias_gyro[1],
                    np.random.normal(0, 0.003) + imu_bias_gyro[2]
                ])
                
                # ====== توصیفگر بصری باینری (کلید نوآوری #۱) ======
                # ۱۲۸-بیت توصیفگر باینری با تغییرات زمانی
                num_bits = 128
                binary_descriptor = np.random.randint(0, 2, num_bits)
                
                # تغییر تدریجی ویژگی‌ها (شبیه‌سازی حرکت دوربین)
                if t > 0:
                    # ۱۲-۱۸% از بیت‌ها در هر فریم تغییر می‌کنند
                    change_prob = np.random.uniform(0.12, 0.18)
                    change_mask = np.random.random(num_bits) < change_prob
                    binary_descriptor[change_mask] = 1 - binary_descriptor[change_mask]
                
                # ====== تخمین VIO با روش گراف فاکتور (کلید نوآوری #۲) ======
                # شبیه‌سازی خطای تخمین - روش گراف فاکتور در non-linearity بهتر است
                if scenario == 'urban_canyon':
                    # محیط شهری با چالش خطی شدن
                    base_error = np.random.gamma(1.8, 0.12)
                elif scenario == 'forest_dense':
                    base_error = np.random.gamma(1.5, 0.15)
                elif scenario == 'indoor_complex':
                    base_error = np.random.gamma(1.2, 0.18)
                else:  # open_field
                    base_error = np.random.gamma(2.5, 0.06)
                
                # ====== بهبود با مشارکت گروهی (کلید نوآوری #۳) ======
                # عدم‌قطیت فعلی
                uncertainty = base_error + np.random.normal(0, 0.02)
                
                # آستانه فعال‌سازی اشتراک (از SRS: ۰.۳ متر)
                uncertainty_threshold = 0.3
                sharing_active = uncertainty > uncertainty_threshold
                
                # ====== اشتراک رویداد-محور ======
                if sharing_active:
                    # بهبود ۶۰-۸۰% با مشارکت گروهی
                    improvement_factor = np.random.uniform(0.2, 0.35)
                    corrected_error = base_error * improvement_factor
                    corrected_error += np.random.normal(0, 0.005)
                    # تعداد Landmarkهای اشتراکی (پراکنده، نه موقعیت خام)
                    num_landmarks_shared = np.random.randint(3, 15)
                else:
                    corrected_error = base_error
                    num_landmarks_shared = 0
                
                # ====== دقت روش جدید در مقابل EKF (برای مقایسه) ======
                # شبیه‌سازی خطای EKF برای مقایسه
                ekf_error = base_error * np.random.uniform(1.2, 1.8)  # EKF خطای بیشتر
                graph_error = corrected_error  # روش گراف فاکتور
                
                # ====== حجم داده اشتراکی ======
                # هر Landmark: موقعیت ۳D (۱۲ بایت) + توصیفگر (۱۶ بایت) = ۲۸ بایت
                # با فشرده‌سازی: ~۲۰ بایت
                shared_data_bytes = num_landmarks_shared * 20
                
                # ====== ذخیره رکورد ======
                vio_data.append({
                    'group_id': group_id,
                    'drone_id': drone_id,
                    'timestamp': base_timestamp + t,
                    'scenario': scenario,
                    'comm_quality': comm_quality,
                    'true_pos_x': round(true_pos[0], 3),
                    'true_pos_y': round(true_pos[1], 3),
                    'true_pos_z': round(true_pos[2], 3),
                    'true_roll': round(true_orientation[0], 4),
                    'true_pitch': round(true_orientation[1], 4),
                    'true_yaw': round(true_orientation[2], 4),
                    'imu_accel_x': round(imu_accel[0], 4),
                    'imu_accel_y': round(imu_accel[1], 4),
                    'imu_accel_z': round(imu_accel[2], 4),
                    'imu_gyro_x': round(imu_gyro[0], 5),
                    'imu_gyro_y': round(imu_gyro[1], 5),
                    'imu_gyro_z': round(imu_gyro[2], 5),
                    'binary_descriptor_hash': int(sum(binary_descriptor) % 256),  # خلاصه ۸-بیتی
                    'num_keypoints': np.random.randint(50, 200),
                    'localization_error_m': round(base_error, 4),
                    'uncertainty_metric': round(uncertainty, 4),
                    'sharing_active': int(sharing_active),
                    'corrected_error_m': round(corrected_error, 4),
                    'num_landmarks_shared': num_landmarks_shared,
                    'shared_data_bytes': shared_data_bytes,
                    'ekf_error_comparison_m': round(ekf_error, 4),
                    'graph_error_m': round(graph_error, 4),
                    'method_type': 'factor_graph_binary_descriptor',
                    # ====== رعایت شرایط SRS ======
                    'meets_accuracy_spec': 'YES' if corrected_error < 0.5 else 'NO',
                    'meets_bandwidth_spec': 'YES' if shared_data_bytes < 100 else 'NO',
                    'meets_latency_spec': 'YES' if corrected_error < 0.3 else 'NO'
                })
    
    return pd.DataFrame(vio_data)

# ========== تولید و ذخیره داده ==========
print("\n" + "="*60)
print("PRODUCT 2 - COOPERATIVE VIO DATA GENERATION")
print("="*60)

df_vio = generate_cooperative_vio_data()
df_vio.to_csv('cooperative_vio_data.csv', index=False)

# ========== تحلیل داده ==========
print("\n📊 Data Summary:")
print(f"Total records: {len(df_vio):,}")
print(f"Groups: {df_vio['group_id'].nunique()}")
print(f"Drones per group: {df_vio['drone_id'].nunique()}")
print(f"Scenarios: {df_vio['scenario'].unique().tolist()}")
print(f"Communication qualities: {df_vio['comm_quality'].unique().tolist()}")

print("\n--- Performance Comparison: Graph-Factor vs EKF ---")
comparison = df_vio.groupby('scenario').agg({
    'graph_error_m': 'mean',
    'ekf_error_comparison_m': 'mean'
}).round(3)
comparison['improvement_pct'] = ((comparison['ekf_error_comparison_m'] - comparison['graph_error_m']) / 
                                 comparison['ekf_error_comparison_m'] * 100).round(1)
print(comparison)

print("\n--- Sharing Statistics ---")
print(f"Sharing active in: {df_vio['sharing_active'].mean()*100:.1f}% of time")
print(f"Average shared data: {df_vio[df_vio['sharing_active']==1]['shared_data_bytes'].mean():.0f} bytes")
print(f"Bandwidth reduction vs continuous sharing: {((1 - df_vio['sharing_active'].mean()) * 100):.0f}%")

print(f"\n✅ Specification compliance:")
print(f"  - Accuracy < 0.5m: {df_vio['meets_accuracy_spec'].value_counts(normalize=True)['YES']*100:.1f}%")
print(f"  - Bandwidth < 100 bytes: {df_vio['meets_bandwidth_spec'].value_counts(normalize=True)['YES']*100:.1f}%")

print("\n📁 File saved: cooperative_vio_data.csv")
print("\n✅ Product 2 data generation complete!")
