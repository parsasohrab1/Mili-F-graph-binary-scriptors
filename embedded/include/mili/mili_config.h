/**
 * @file mili_config.h
 * @brief SRS-aligned embedded configuration for STM32H7
 */
#ifndef MILI_CONFIG_H
#define MILI_CONFIG_H

/* Platform */
#define MILI_CPU_FREQ_HZ           480000000U
#define MILI_STATE_UPDATE_HZ       20U
#define MILI_STATE_PERIOD_MS       (1000U / MILI_STATE_UPDATE_HZ)

/* Camera - Global Shutter 640x480 @ 30fps */
#define MILI_CAM_WIDTH             640U
#define MILI_CAM_HEIGHT            480U
#define MILI_CAM_FPS               30U
#define MILI_CAM_FRAME_BYTES         (MILI_CAM_WIDTH * MILI_CAM_HEIGHT)

/* IMU - Bosch BMI088 */
#define MILI_IMU_SAMPLE_HZ         200U
#define MILI_IMU_GRAVITY           9.81f

/* BNN - Product 1 */
#define MILI_BNN_SPI_CLOCK_HZ      20000000U
#define MILI_BNN_MAX_KEYPOINTS     200U
#define MILI_DESCRIPTOR_BITS       128U
#define MILI_DESCRIPTOR_BYTES      16U

/* Factor graph */
#define MILI_FG_MEMORY_BUDGET      (2U * 1024U * 1024U)
#define MILI_FG_MAX_POSES          12U
#define MILI_FG_MAX_LANDMARKS      80U
#define MILI_FG_MAX_OPT_MS         5U

/* Sharing */
#define MILI_UNCERTAINTY_THRESHOLD 0.3f
#define MILI_MAX_BANDWIDTH_BPS     51200U
#define MILI_MAX_DRONES            12U
#define MILI_LANDMARK_COMPRESSED   20U

/* Performance budgets (ms) */
#define MILI_BUDGET_BNN_MS         2U
#define MILI_BUDGET_VIO_MS         5U
#define MILI_BUDGET_SHARE_MS       20U

/* RTOS queue depths */
#define MILI_QUEUE_FRAMES          2U
#define MILI_QUEUE_DESCRIPTORS     2U
#define MILI_QUEUE_STATES        4U

/* Stability test */
#define MILI_STABILITY_MIN_SEC     3600U

#endif /* MILI_CONFIG_H */
