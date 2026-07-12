#include "mili/drivers/bnn_protocol.h"

uint8_t bnn_checksum(const uint8_t *header7, const uint8_t *payload, uint16_t plen)
{
    uint32_t sum = 0;
    for (uint32_t i = 0; i < 7U; i++) sum += header7[i];
    for (uint16_t i = 0; i < plen; i++) sum += payload[i];
    return (uint8_t)(sum & 0xFFU);
}

int bnn_frame_pack(uint8_t cmd, uint8_t seq, const uint8_t *payload, uint16_t plen,
                   uint8_t *out, uint32_t out_cap, uint32_t *out_len)
{
    uint32_t total = BNN_PROTO_HEADER_SIZE + plen;
    if (!out || !out_len || out_cap < total) return -1;

    out[0] = (uint8_t)(BNN_PROTO_MAGIC >> 8);
    out[1] = (uint8_t)(BNN_PROTO_MAGIC & 0xFFU);
    out[2] = cmd;
    out[3] = (uint8_t)(plen >> 8);
    out[4] = (uint8_t)(plen & 0xFFU);
    out[5] = seq;
    out[6] = 0U;
    out[7] = 0U;

    if (payload && plen > 0) {
        for (uint16_t i = 0; i < plen; i++) {
            out[BNN_PROTO_HEADER_SIZE + i] = payload[i];
        }
    }
    out[7] = bnn_checksum(out, out + BNN_PROTO_HEADER_SIZE, plen);
    *out_len = total;
    return 0;
}

int bnn_frame_unpack(const uint8_t *data, uint32_t len, bnn_frame_header_t *hdr,
                     const uint8_t **payload)
{
    if (!data || !hdr || len < BNN_PROTO_HEADER_SIZE) return -1;

    hdr->magic = (uint16_t)((data[0] << 8) | data[1]);
    hdr->cmd = data[2];
    hdr->payload_len = (uint16_t)((data[3] << 8) | data[4]);
    hdr->sequence = data[5];
    hdr->flags = data[6];
    hdr->checksum = data[7];

    if (hdr->magic != BNN_PROTO_MAGIC) return -2;
    if (len < BNN_PROTO_HEADER_SIZE + hdr->payload_len) return -3;

    uint8_t expected = bnn_checksum(data, data + BNN_PROTO_HEADER_SIZE, hdr->payload_len);
    if (expected != hdr->checksum) return -4;

    if (payload) *payload = data + BNN_PROTO_HEADER_SIZE;
    return 0;
}
