#include "mili/drivers/camera_dcmi.h"
#include <string.h>

static mili_camera_callback_t s_cb;
static void *s_user;
static int s_running;

int mili_camera_init(void) { return 0; }

int mili_camera_start(mili_camera_callback_t cb, void *user)
{
    s_cb = cb;
    s_user = user;
    s_running = 1;
    return 0;
}

void mili_camera_stop(void) { s_running = 0; }

int mili_camera_capture(mili_camera_frame_t *frame)
{
    if (!frame) return -1;
    return mili_camera_sim_fill(frame, frame->frame_id);
}

int mili_camera_sim_fill(mili_camera_frame_t *frame, uint32_t frame_id)
{
    if (!frame) return -1;
    memset(frame->data, (uint8_t)(frame_id & 0xFF), MILI_CAM_FRAME_BYTES);
    frame->frame_id = frame_id;
    frame->timestamp_us = (uint64_t)frame_id * 33333ULL;
    if (s_running && s_cb) s_cb(frame, s_user);
    return 0;
}
