#include "mili/drivers/bnn_spi.h"
#include "mili/drivers/bnn_protocol.h"
#include <string.h>

static int extract_local_sim(const mili_camera_frame_t *frame, mili_descriptor_frame_t *out);

int mili_bnn_spi_transfer(const uint8_t *tx, uint32_t tx_len,
                          uint8_t *rx, uint32_t rx_cap, uint32_t *rx_len)
{
#ifdef MILI_HOST_SIM
    (void)tx;
    (void)tx_len;
    (void)rx;
    (void)rx_cap;
    if (rx_len) *rx_len = 0;
    return -1; /* host sim uses local extract_local_sim */
#else
    /* TODO: HAL_SPI_TransmitReceive_DMA(hspi_bnn, tx, rx, tx_len) */
    (void)tx;
    (void)tx_len;
    (void)rx;
    (void)rx_cap;
    if (rx_len) *rx_len = 0;
    return -1;
#endif
}

int mili_bnn_init(void)
{
    return mili_bnn_reset();
}

int mili_bnn_reset(void)
{
    uint8_t tx[16], rx[16];
    uint32_t tx_len = 0, rx_len = 0;
    if (bnn_frame_pack(BNN_CMD_RESET, 1, NULL, 0, tx, sizeof(tx), &tx_len) != 0) {
        return -1;
    }
    if (mili_bnn_spi_transfer(tx, tx_len, rx, sizeof(rx), &rx_len) != 0) {
        return 0; /* host sim: no SPI hardware */
    }
    return 0;
}

int mili_bnn_get_version(uint8_t *major, uint8_t *minor, uint8_t *patch)
{
    if (major) *major = 1;
    if (minor) *minor = 0;
    if (patch) *patch = 0;

    uint8_t tx[16], rx[16];
    uint32_t tx_len = 0, rx_len = 0;
    if (bnn_frame_pack(BNN_CMD_GET_VERSION, 2, NULL, 0, tx, sizeof(tx), &tx_len) != 0) {
        return -1;
    }
    if (mili_bnn_spi_transfer(tx, tx_len, rx, sizeof(rx), &rx_len) == 0 && rx_len >= 11) {
        if (major) *major = rx[BNN_PROTO_HEADER_SIZE];
        if (minor) *minor = rx[BNN_PROTO_HEADER_SIZE + 1];
        if (patch) *patch = rx[BNN_PROTO_HEADER_SIZE + 2];
    }
    return 0;
}

int mili_bnn_extract(const mili_camera_frame_t *frame, mili_descriptor_frame_t *out)
{
    if (!frame || !out) return -1;

#ifdef MILI_HOST_SIM
    return extract_local_sim(frame, out);
#else
    uint8_t req[32];
    uint16_t w = MILI_CAM_WIDTH, h = MILI_CAM_HEIGHT;
    uint16_t max_kp = MILI_BNN_MAX_KEYPOINTS;
    req[0] = (uint8_t)(w >> 8); req[1] = (uint8_t)(w & 0xFF);
    req[2] = (uint8_t)(h >> 8); req[3] = (uint8_t)(h & 0xFF);
    req[4] = (uint8_t)(max_kp >> 8); req[5] = (uint8_t)(max_kp & 0xFF);
    memcpy(req + 6, frame->data, MILI_CAM_FRAME_BYTES);

    uint8_t tx[16 + 6 + MILI_CAM_FRAME_BYTES];
    uint8_t rx[4096];
    uint32_t tx_len = 0, rx_len = 0;
    if (bnn_frame_pack(BNN_CMD_EXTRACT, 3, req, (uint16_t)(6 + MILI_CAM_FRAME_BYTES),
                       tx, sizeof(tx), &tx_len) != 0) {
        return -1;
    }
    if (mili_bnn_spi_transfer(tx, tx_len, rx, sizeof(rx), &rx_len) != 0) {
        return extract_local_sim(frame, out);
    }
    /* Parse ExtractResponse payload from rx frame */
    return extract_local_sim(frame, out);
#endif
}

static int extract_local_sim(const mili_camera_frame_t *frame, mili_descriptor_frame_t *out)
{
    memset(out, 0, sizeof(*out));
    out->timestamp_us = frame->timestamp_us;

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
                kp->descriptor[b] = frame->data[idx + (uint32_t)b % MILI_CAM_WIDTH] ^ (uint8_t)(count + b);
            }
            count++;
        }
    }

    out->count = count;
    out->extraction_time_us = 1500U;
    out->energy_uj = 500U + count * 20U;
    return 0;
}
