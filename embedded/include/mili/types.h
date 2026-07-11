/**
 * @file types.h
 * @brief Core data types for embedded VIO pipeline
 */
#ifndef MILI_TYPES_H
#define MILI_TYPES_H

#include <stdint.h>
#include <stdbool.h>
#include "mili_config.h"

typedef struct {
    float x, y, z;
} mili_vec3_t;

typedef struct {
    float roll, pitch, yaw;
} mili_euler_t;

typedef struct {
    mili_vec3_t position;
    mili_euler_t orientation;
} mili_pose_t;

typedef struct {
    mili_vec3_t accel;
    mili_vec3_t gyro;
    uint64_t timestamp_us;
} mili_imu_sample_t;

typedef struct {
    float u, v;
    float response;
    uint8_t descriptor[MILI_DESCRIPTOR_BYTES];
    uint16_t keypoint_id;
} mili_keypoint_t;

typedef struct {
    mili_keypoint_t keypoints[MILI_BNN_MAX_KEYPOINTS];
    uint16_t count;
    uint64_t timestamp_us;
    uint32_t extraction_time_us;
    uint32_t energy_uj;
} mili_descriptor_frame_t;

typedef struct {
    mili_pose_t pose;
    float uncertainty;
    float covariance[6];  /* diagonal approximation */
    uint64_t timestamp_us;
    uint32_t opt_time_us;
} mili_state_estimate_t;

typedef struct {
    uint8_t data[MILI_CAM_FRAME_BYTES];
    uint64_t timestamp_us;
    uint32_t frame_id;
} mili_camera_frame_t;

typedef enum {
    MILI_COMM_UWB = 0,
    MILI_COMM_WIFI = 1
} mili_comm_type_t;

#endif /* MILI_TYPES_H */
