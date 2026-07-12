/**
 * @file bmi088_hal.h
 * @brief Bosch BMI088 SPI HAL
 */
#ifndef MILI_BMI088_HAL_H
#define MILI_BMI088_HAL_H

#include <stdint.h>
#include "mili/types.h"

#define BMI088_ACC_CHIP_ID   0x1EU
#define BMI088_GYR_CHIP_ID   0x0FU
#define MILI_BMI088_FIFO_DEPTH 32U

int mili_bmi088_hal_init(void);
int mili_bmi088_hal_read(mili_imu_sample_t *sample);
int mili_bmi088_hal_read_batch(mili_imu_sample_t *buf, uint16_t max, uint16_t *count);
uint8_t mili_bmi088_hal_probe(void);

#endif
