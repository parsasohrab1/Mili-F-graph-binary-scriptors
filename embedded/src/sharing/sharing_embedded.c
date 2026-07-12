#include "mili/sharing/sharing_embedded.h"
#include "mili/drivers/comm_uwb.h"
#include "mili/mili_config.h"
#include <string.h>

bool mili_share_should_trigger(float uncertainty)
{
    return uncertainty > MILI_UNCERTAINTY_THRESHOLD;
}

int mili_share_encode(const mili_share_meta_t *meta,
                      const mili_keypoint_t *keypoints, uint8_t count,
                      uint8_t *buf, uint16_t buf_size, uint16_t *out_len)
{
    if (!meta || !buf || !out_len) return -1;
    uint16_t needed = MILI_SHARE_HEADER_SIZE + (uint16_t)count * MILI_SHARE_LM_SIZE;
    if (needed > buf_size) return -1;

    buf[0] = 0x4D; buf[1] = 0x49;
    buf[2] = 1;    /* version */
    buf[3] = 0x01; /* LANDMARK_SHARE */
    buf[4] = meta->drone_id;
    buf[5] = (uint8_t)(meta->timestamp_ns >> 24);
    buf[6] = (uint8_t)(meta->timestamp_ns >> 16);
    buf[7] = (uint8_t)(meta->timestamp_ns >> 8);
    buf[8] = (uint8_t)(meta->timestamp_ns);
    buf[9] = count;
    uint16_t unc_q = (uint16_t)(meta->uncertainty * 10.0f);
    buf[10] = (uint8_t)(unc_q >> 8);
    buf[11] = (uint8_t)(unc_q);
    buf[12] = 0; /* seq */
    buf[13] = 0; /* checksum */

    uint16_t off = MILI_SHARE_HEADER_SIZE;
    for (uint8_t i = 0; i < count && keypoints; i++) {
        buf[off++] = (uint8_t)(keypoints[i].keypoint_id >> 8);
        buf[off++] = (uint8_t)(keypoints[i].keypoint_id);
        memcpy(&buf[off], keypoints[i].descriptor, MILI_DESCRIPTOR_BYTES);
        off += MILI_DESCRIPTOR_BYTES;
        buf[off++] = (uint8_t)(keypoints[i].response * 100.0f);
        buf[off++] = meta->drone_id & 0x0F;
    }

    *out_len = needed;
    return 0;
}

int mili_share_decode(const uint8_t *buf, uint16_t len,
                      mili_share_meta_t *meta,
                      mili_keypoint_t *keypoints, uint8_t max_kp, uint8_t *out_count)
{
    if (!buf || len < MILI_SHARE_HEADER_SIZE || !meta || !out_count) return -1;
    meta->drone_id = buf[4];
    meta->timestamp_ns = ((uint32_t)buf[5] << 24) | ((uint32_t)buf[6] << 16)
                       | ((uint32_t)buf[7] << 8) | buf[8];
    meta->num_landmarks = buf[9];
    uint16_t unc_q = ((uint16_t)buf[10] << 8) | buf[11];
    meta->uncertainty = unc_q / 10.0f;

    uint8_t n = meta->num_landmarks < max_kp ? meta->num_landmarks : max_kp;
    uint16_t off = MILI_SHARE_HEADER_SIZE;
    for (uint8_t i = 0; i < n && keypoints; i++) {
        if (off + MILI_SHARE_LM_SIZE > len) break;
        keypoints[i].keypoint_id = ((uint16_t)buf[off] << 8) | buf[off + 1];
        memcpy(keypoints[i].descriptor, &buf[off + 2], MILI_DESCRIPTOR_BYTES);
        keypoints[i].response = buf[off + 18] / 100.0f;
        off += MILI_SHARE_LM_SIZE;
    }
    *out_count = n;
    return 0;
}

int mili_share_send_uwb(const mili_share_meta_t *meta,
                        const mili_keypoint_t *keypoints, uint8_t count)
{
    uint8_t buf[512];
    uint16_t len = 0;
    if (mili_share_encode(meta, keypoints, count, buf, sizeof(buf), &len) != 0) {
        return -1;
    }
    return mili_uwb_broadcast(buf, len);
}

int mili_share_recv_uwb(mili_share_meta_t *meta,
                        mili_keypoint_t *keypoints, uint8_t max_kp, uint8_t *out_count)
{
    uint8_t buf[512];
    uint16_t len = 0;
    if (mili_uwb_recv(buf, sizeof(buf), &len) != 0 || len == 0) {
        if (out_count) *out_count = 0;
        return 0;
    }
    return mili_share_decode(buf, len, meta, keypoints, max_kp, out_count);
}
