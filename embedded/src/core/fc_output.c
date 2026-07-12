#include "mili/fc_output.h"
#include <string.h>

uint8_t mili_fc_checksum(const uint8_t *data, uint32_t len)
{
    uint8_t sum = 0;
    for (uint32_t i = 0; i < len; i++) {
        sum ^= data[i];
    }
    return sum;
}

int mili_fc_pack(const mili_fc_state_t *state, uint8_t *out, uint32_t out_len)
{
    if (!state || !out || out_len < MILI_FC_FRAME_SIZE) {
        return -1;
    }

    mili_fc_frame_t frame;
    memset(&frame, 0, sizeof(frame));
    frame.magic = MILI_FC_FRAME_MAGIC;
    frame.version = MILI_FC_FRAME_VERSION;
    frame.flags = 0x01U;
    if (state->sharing_active) frame.flags |= 0x02U;
    if (state->loop_closure_active) frame.flags |= 0x04U;
    frame.timestamp_us = state->timestamp_us;
    frame.position[0] = state->pose.position.x;
    frame.position[1] = state->pose.position.y;
    frame.position[2] = state->pose.position.z;
    frame.orientation[0] = state->pose.orientation.roll;
    frame.orientation[1] = state->pose.orientation.pitch;
    frame.orientation[2] = state->pose.orientation.yaw;
    frame.uncertainty = state->uncertainty;
    memcpy(frame.covariance_diag, state->covariance_diag, sizeof(frame.covariance_diag));
    frame.opt_time_us = state->opt_time_us;
    frame.checksum = 0;

    memcpy(out, &frame, MILI_FC_FRAME_SIZE - 1U);
    out[MILI_FC_FRAME_SIZE - 1U] = mili_fc_checksum(out, MILI_FC_FRAME_SIZE - 1U);
    return (int)MILI_FC_FRAME_SIZE;
}

int mili_fc_unpack(const uint8_t *data, uint32_t len, mili_fc_state_t *state)
{
    if (!data || !state || len < MILI_FC_FRAME_SIZE) {
        return -1;
    }

    const mili_fc_frame_t *frame = (const mili_fc_frame_t *)data;
    if (frame->magic != MILI_FC_FRAME_MAGIC) {
        return -2;
    }
    uint8_t expected = mili_fc_checksum(data, MILI_FC_FRAME_SIZE - 1U);
    if (expected != data[MILI_FC_FRAME_SIZE - 1U]) {
        return -3;
    }

    state->timestamp_us = frame->timestamp_us;
    state->pose.position.x = frame->position[0];
    state->pose.position.y = frame->position[1];
    state->pose.position.z = frame->position[2];
    state->pose.orientation.roll = frame->orientation[0];
    state->pose.orientation.pitch = frame->orientation[1];
    state->pose.orientation.yaw = frame->orientation[2];
    state->uncertainty = frame->uncertainty;
    memcpy(state->covariance_diag, frame->covariance_diag, sizeof(state->covariance_diag));
    state->opt_time_us = frame->opt_time_us;
    state->sharing_active = (frame->flags & 0x02U) != 0;
    state->loop_closure_active = (frame->flags & 0x04U) != 0;
    return 0;
}
