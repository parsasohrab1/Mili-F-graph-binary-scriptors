#include "mili/drivers/imu_bmi088.h"
#include "mili/hal/bmi088_hal.h"

int mili_imu_init(void)
{
    return mili_bmi088_hal_init();
}

int mili_imu_read(mili_imu_sample_t *sample)
{
    if (!sample) return -1;
    return mili_bmi088_hal_read(sample);
}

int mili_imu_read_batch(mili_imu_sample_t *buf, uint16_t max, uint16_t *count)
{
    return mili_bmi088_hal_read_batch(buf, max, count);
}

int mili_imu_sim_fill(mili_imu_sample_t *sample, uint64_t timestamp_us)
{
    sample->timestamp_us = timestamp_us;
    return mili_bmi088_hal_read(sample);
}
