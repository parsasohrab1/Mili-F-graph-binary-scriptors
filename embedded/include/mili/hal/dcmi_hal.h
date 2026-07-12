/**
 * @file dcmi_hal.h
 * @brief DCMI + DMA HAL for global-shutter camera
 */
#ifndef MILI_DCMI_HAL_H
#define MILI_DCMI_HAL_H

#include <stdint.h>
#include "mili/types.h"

typedef void (*mili_dcmi_frame_cb_t)(const mili_camera_frame_t *frame, void *user);

int mili_dcmi_hal_init(void);
int mili_dcmi_hal_start_dma(mili_dcmi_frame_cb_t cb, void *user);
void mili_dcmi_hal_stop(void);
int mili_dcmi_hal_capture_sync(mili_camera_frame_t *frame);

/* Called from DMA IRQ on STM32 — forwards completed frame */
void mili_dcmi_hal_dma_complete_isr(uint8_t *frame_buf, uint32_t frame_id, uint64_t ts_us);

#endif
