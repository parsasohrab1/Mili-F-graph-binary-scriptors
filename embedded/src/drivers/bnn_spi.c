#include "mili/drivers/bnn_spi.h"
#include <string.h>

/* BNN protocol - mirrors Python mili_vio/descriptors/bnn/protocol.py */
#define BNN_MAGIC 0xB1B1

int mili_bnn_init(void) { return 0; }
int mili_bnn_reset(void) { return 0; }

int mili_bnn_extract(const mili_camera_frame_t *frame, mili_descriptor_frame_t *out)
{
    if (!frame || !out) return -1;

    memset(out, 0, sizeof(*out));
    out->timestamp_us = frame->timestamp_us;

    /* Simulated extraction: derive keypoints from image gradient */
    uint16_t count = 0;
    const uint32_t stride = MILI_CAM_WIDTH / 16;

    for (uint32_t y = stride; y < MILI_CAM_HEIGHT - stride && count < MILI_BNN_MAX_KEYPOINTS; y += stride) {
        for (uint32_t x = stride; x < MILI_CAM_WIDTH - stride && count < MILI_BNN_MAX_KEYPOINTS; x += stride) {
            uint32_t idx = y * MILI_CAM_WIDTH + x;
            uint8_t g = frame->data[idx];
            if (g < 64 || g > 200) continue;

            mili_keypoint_t *kp = &out->keypoints[count];
            kp->u = (float)x;
            kp->v = (float)y;
            kp->response = (float)g / 255.0f;
            kp->keypoint_id = count;

            for (int b = 0; b < MILI_DESCRIPTOR_BYTES; b++) {
                kp->descriptor[b] = frame->data[idx + b % MILI_CAM_WIDTH] ^ (uint8_t)(count + b);
            }
            count++;
        }
    }

    out->count = count;
    out->extraction_time_us = 1500U; /* target < 2ms */
    out->energy_uj = 500U + count * 20U;
    return 0;
}
