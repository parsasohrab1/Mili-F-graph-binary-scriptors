#include "mili/hal/dcmi_hal.h"
#include "mili/mili_config.h"
#include <string.h>

static mili_dcmi_frame_cb_t s_cb;
static void *s_user;
static int s_active;
static uint8_t s_dma_buf[MILI_CAM_FRAME_BYTES];

int mili_dcmi_hal_init(void)
{
    s_active = 0;
    return 0;
}

int mili_dcmi_hal_start_dma(mili_dcmi_frame_cb_t cb, void *user)
{
    s_cb = cb;
    s_user = user;
    s_active = 1;
#ifndef MILI_HOST_SIM
    /* TODO: HAL_DCMI_Init + DMA double-buffer:
     *   HAL_DCMI_Start_DMA(&hdcmi, DCMI_MODE_CONTINUOUS, (uint32_t)s_dma_buf, MILI_CAM_FRAME_BYTES/4);
     */
#endif
    return 0;
}

void mili_dcmi_hal_stop(void)
{
    s_active = 0;
#ifndef MILI_HOST_SIM
    /* HAL_DCMI_Stop(&hdcmi); */
#endif
}

void mili_dcmi_hal_dma_complete_isr(uint8_t *frame_buf, uint32_t frame_id, uint64_t ts_us)
{
    if (!s_active || !s_cb || !frame_buf) return;
    mili_camera_frame_t frame;
    memcpy(frame.data, frame_buf, MILI_CAM_FRAME_BYTES);
    frame.frame_id = frame_id;
    frame.timestamp_us = ts_us;
    s_cb(&frame, s_user);
}

int mili_dcmi_hal_capture_sync(mili_camera_frame_t *frame)
{
    if (!frame) return -1;
#ifdef MILI_HOST_SIM
    memset(s_dma_buf, (uint8_t)(frame->frame_id & 0xFF), MILI_CAM_FRAME_BYTES);
    memcpy(frame->data, s_dma_buf, MILI_CAM_FRAME_BYTES);
    if (s_active && s_cb) s_cb(frame, s_user);
    return 0;
#else
    /* Poll DCMI frame-ready flag or copy from active DMA buffer */
    memcpy(frame->data, s_dma_buf, MILI_CAM_FRAME_BYTES);
    return 0;
#endif
}
