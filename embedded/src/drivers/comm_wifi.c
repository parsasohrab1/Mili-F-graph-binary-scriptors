#include "mili/drivers/comm_wifi.h"

static uint8_t s_wifi_drone_id;

int mili_wifi_init(uint8_t drone_id)
{
    s_wifi_drone_id = drone_id;
    return 0;
}

int mili_wifi_send(const uint8_t *data, uint16_t len)
{
    (void)data; (void)len; (void)s_wifi_drone_id;
    return 0;
}

int mili_wifi_recv(uint8_t *data, uint16_t max_len, uint16_t *out_len)
{
    if (!out_len) return -1;
    *out_len = 0;
    (void)data; (void)max_len;
    return 0;
}
