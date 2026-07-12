#include "mili/hal/bmi088_hal.h"
#include "mili/mili_config.h"
#include <string.h>

#ifndef MILI_HOST_SIM
/* STM32: implement with HAL_SPI_TransmitReceive */
static int bmi088_spi_xfer(uint8_t reg, uint8_t *rx, uint16_t len)
{
    (void)reg; (void)rx; (void)len;
    return -1;
}
#endif

static int bmi088_sim_fill(mili_imu_sample_t *sample, uint64_t ts_us)
{
    sample->timestamp_us = ts_us;
    sample->accel.x = 0.0f;
    sample->accel.y = 0.0f;
    sample->accel.z = MILI_IMU_GRAVITY;
    sample->gyro.x = 0.01f;
    sample->gyro.y = 0.01f;
    sample->gyro.z = 0.05f;
    return 0;
}

int mili_bmi088_hal_init(void)
{
#ifdef MILI_HOST_SIM
    return 0;
#else
    uint8_t id = 0;
    if (bmi088_spi_xfer(0x00, &id, 1) != 0) return -1;
    return (id == BMI088_ACC_CHIP_ID) ? 0 : -1;
#endif
}

uint8_t mili_bmi088_hal_probe(void)
{
#ifdef MILI_HOST_SIM
    return BMI088_ACC_CHIP_ID;
#else
    uint8_t id = 0;
    bmi088_spi_xfer(0x00, &id, 1);
    return id;
#endif
}

int mili_bmi088_hal_read(mili_imu_sample_t *sample)
{
    if (!sample) return -1;
#ifdef MILI_HOST_SIM
    return bmi088_sim_fill(sample, sample->timestamp_us);
#else
    /* Read ACC + GYR registers via SPI burst */
    uint8_t raw[12];
    if (bmi088_spi_xfer(0x12, raw, sizeof(raw)) != 0) return -1;
    sample->accel.x = (int16_t)(raw[1] << 8 | raw[0]) * 0.001f;
    sample->accel.y = (int16_t)(raw[3] << 8 | raw[2]) * 0.001f;
    sample->accel.z = (int16_t)(raw[5] << 8 | raw[4]) * 0.001f;
    sample->gyro.x = (int16_t)(raw[7] << 8 | raw[6]) * 0.001f;
    sample->gyro.y = (int16_t)(raw[9] << 8 | raw[8]) * 0.001f;
    sample->gyro.z = (int16_t)(raw[11] << 8 | raw[10]) * 0.001f;
    return 0;
#endif
}

int mili_bmi088_hal_read_batch(mili_imu_sample_t *buf, uint16_t max, uint16_t *count)
{
    if (!buf || !count) return -1;
    uint16_t n = max < MILI_BMI088_FIFO_DEPTH ? max : MILI_BMI088_FIFO_DEPTH;
    for (uint16_t i = 0; i < n; i++) {
        if (mili_bmi088_hal_read(&buf[i]) != 0) return -1;
    }
    *count = n;
    return 0;
}
