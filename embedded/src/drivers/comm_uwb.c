#include "mili/drivers/comm_uwb.h"
#include <string.h>

static uint8_t s_drone_id;
static uint32_t s_bytes_sent;

int mili_uwb_init(uint8_t drone_id)
{
    s_drone_id = drone_id;
    s_bytes_sent = 0;
    return 0;
}

int mili_uwb_send(const uint8_t *data, uint16_t len)
{
    if (!data || len == 0) return -1;
    s_bytes_sent += len;
    (void)s_drone_id;
    return 0;
}

int mili_uwb_recv(uint8_t *data, uint16_t max_len, uint16_t *out_len)
{
    if (!data || !out_len) return -1;
    *out_len = 0;
    return 0;
}

int mili_uwb_broadcast(const uint8_t *data, uint16_t len)
{
    return mili_uwb_send(data, len);
}
