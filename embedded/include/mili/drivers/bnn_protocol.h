/**
 * @file bnn_protocol.h
 * @brief BNN SPI protocol — mirrors Python mili_vio/descriptors/bnn/protocol.py
 */
#ifndef MILI_BNN_PROTOCOL_H
#define MILI_BNN_PROTOCOL_H

#include <stdint.h>
#include "mili/pack.h"

#define BNN_PROTO_MAGIC        0xB1B1U
#define BNN_PROTO_HEADER_SIZE  8U
#define BNN_CMD_RESET          0x01U
#define BNN_CMD_EXTRACT        0x10U
#define BNN_CMD_GET_VERSION    0x12U
#define BNN_STATUS_OK          0x00U

MILI_PACK_BEGIN()
typedef struct MILI_PACKED {
    uint16_t magic;
    uint8_t  cmd;
    uint16_t payload_len;
    uint8_t  sequence;
    uint8_t  flags;
    uint8_t  checksum;
} bnn_frame_header_t;
MILI_PACK_END()

uint8_t bnn_checksum(const uint8_t *header7, const uint8_t *payload, uint16_t plen);
int bnn_frame_pack(uint8_t cmd, uint8_t seq, const uint8_t *payload, uint16_t plen,
                   uint8_t *out, uint32_t out_cap, uint32_t *out_len);
int bnn_frame_unpack(const uint8_t *data, uint32_t len, bnn_frame_header_t *hdr,
                     const uint8_t **payload);

#endif /* MILI_BNN_PROTOCOL_H */
