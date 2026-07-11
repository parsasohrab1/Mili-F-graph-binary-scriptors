/**
 * @file camera_dcmi.h
 * @brief DCMI camera driver - 640x480 grayscale @ 30fps
 */
#ifndef MILI_CAMERA_DCMI_H
#define MILI_CAMERA_DCMI_H

#include "mili/types.h"

typedef void (*mili_camera_callback_t)(const mili_camera_frame_t *frame, void *user);

int mili_camera_init(void);
int mili_camera_start(mili_camera_callback_t cb, void *user);
void mili_camera_stop(void);
int mili_camera_capture(mili_camera_frame_t *frame);

/* Host simulation */
int mili_camera_sim_fill(mili_camera_frame_t *frame, uint32_t frame_id);

#endif
