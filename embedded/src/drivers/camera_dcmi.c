#include "mili/drivers/camera_dcmi.h"
#include "mili/hal/dcmi_hal.h"
#include <string.h>

static mili_camera_callback_t s_app_cb;
static void *s_app_user;

static void dcmi_forward_cb(const mili_camera_frame_t *frame, void *user)
{
    (void)user;
    if (s_app_cb) s_app_cb(frame, s_app_user);
}

int mili_camera_init(void)
{
    return mili_dcmi_hal_init();
}

int mili_camera_start(mili_camera_callback_t cb, void *user)
{
    s_app_cb = cb;
    s_app_user = user;
    return mili_dcmi_hal_start_dma(dcmi_forward_cb, NULL);
}

void mili_camera_stop(void)
{
    mili_dcmi_hal_stop();
}

int mili_camera_capture(mili_camera_frame_t *frame)
{
    if (!frame) return -1;
    return mili_dcmi_hal_capture_sync(frame);
}

int mili_camera_sim_fill(mili_camera_frame_t *frame, uint32_t frame_id)
{
    if (!frame) return -1;
    memset(frame->data, (uint8_t)(frame_id & 0xFF), MILI_CAM_FRAME_BYTES);
    frame->frame_id = frame_id;
    frame->timestamp_us = (uint64_t)frame_id * 33333ULL;
    return mili_dcmi_hal_capture_sync(frame);
}
