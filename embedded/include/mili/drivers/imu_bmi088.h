/**
 * @file imu_bmi088.h
 * @brief Bosch BMI088 IMU driver (SPI)
 */
#ifndef MILI_IMU_BMI088_H
#define MILI_IMU_BMI088_H

#include "mili/types.h"

#define MILI_IMU_FIFO_DEPTH  32U

int mili_imu_init(void);
int mili_imu_read(mili_imu_sample_t *sample);
int mili_imu_read_batch(mili_imu_sample_t *buf, uint16_t max, uint16_t *count);

/* Host simulation */
int mili_imu_sim_fill(mili_imu_sample_t *sample, uint64_t timestamp_us);

#endif
