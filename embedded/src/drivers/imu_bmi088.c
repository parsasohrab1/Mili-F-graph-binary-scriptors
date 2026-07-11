#include "mili/drivers/imu_bmi088.h"
#include <math.h>

#ifndef MILI_HOST_SIM
/* STM32: HAL_SPI + BMI088 register map */
#endif

int mili_imu_init(void) { return 0; }

int mili_imu_read(mili_imu_sample_t *sample)
{
    if (!sample) return -1;
    return mili_imu_sim_fill(sample, sample->timestamp_us);
}

int mili_imu_read_batch(mili_imu_sample_t *buf, uint16_t max, uint16_t *count)
{
    if (!buf || !count) return -1;
    uint16_t n = max < MILI_IMU_FIFO_DEPTH ? max : MILI_IMU_FIFO_DEPTH;
    for (uint16_t i = 0; i < n; i++) {
        mili_imu_sim_fill(&buf[i], buf[i].timestamp_us);
    }
    *count = n;
    return 0;
}

int mili_imu_sim_fill(mili_imu_sample_t *sample, uint64_t timestamp_us)
{
    sample->timestamp_us = timestamp_us;
    sample->accel.x = 0.0f;
    sample->accel.y = 0.0f;
    sample->accel.z = MILI_IMU_GRAVITY;
    sample->gyro.x = 0.01f;
    sample->gyro.y = 0.01f;
    sample->gyro.z = 0.05f;
    return 0;
}
