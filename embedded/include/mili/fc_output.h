/**
 * @file fc_output.h
 * @brief Flight-controller output API (pose + covariance) for main STM32H7
 *
 * Binary frame sent over UART/SPI to the primary flight controller.
 * Layout matches Python mili_vio.runtime.flight_controller.pack_state_estimate().
 */
#ifndef MILI_FC_OUTPUT_H
#define MILI_FC_OUTPUT_H

#include <stdint.h>
#include <stdbool.h>
#include "mili/types.h"
#include "mili/pack.h"

#define MILI_FC_FRAME_MAGIC        0xFC01U
#define MILI_FC_FRAME_VERSION      1U
#define MILI_FC_FRAME_SIZE         69U

MILI_PACK_BEGIN()
typedef struct MILI_PACKED {
    uint16_t magic;
    uint8_t  version;
    uint8_t  flags;
    uint64_t timestamp_us;
    float    position[3];
    float    orientation[3];
    float    uncertainty;
    float    covariance_diag[6];
    uint32_t opt_time_us;
    uint8_t  checksum;
} mili_fc_frame_t;
MILI_PACK_END()

typedef struct {
    mili_pose_t pose;
    float uncertainty;
    float covariance_diag[6];
    uint64_t timestamp_us;
    uint32_t opt_time_us;
    bool sharing_active;
    bool loop_closure_active;
} mili_fc_state_t;

uint8_t mili_fc_checksum(const uint8_t *data, uint32_t len);
int mili_fc_pack(const mili_fc_state_t *state, uint8_t *out, uint32_t out_len);
int mili_fc_unpack(const uint8_t *data, uint32_t len, mili_fc_state_t *state);

#endif /* MILI_FC_OUTPUT_H */
