/**
 * @file sharing_embedded.h
 * @brief Compressed landmark UDP sharing (FR-3 embedded port)
 */
#ifndef MILI_SHARING_EMBEDDED_H
#define MILI_SHARING_EMBEDDED_H

#include <stdint.h>
#include <stdbool.h>
#include "mili/types.h"

#define MILI_SHARE_HEADER_SIZE   14U
#define MILI_SHARE_LM_SIZE       20U

typedef struct {
    uint8_t drone_id;
    uint32_t timestamp_ns;
    float uncertainty;
    uint8_t num_landmarks;
} mili_share_meta_t;

int mili_share_encode(const mili_share_meta_t *meta,
                      const mili_keypoint_t *keypoints, uint8_t count,
                      uint8_t *buf, uint16_t buf_size, uint16_t *out_len);

int mili_share_decode(const uint8_t *buf, uint16_t len,
                      mili_share_meta_t *meta,
                      mili_keypoint_t *keypoints, uint8_t max_kp, uint8_t *out_count);

bool mili_share_should_trigger(float uncertainty);

#endif
