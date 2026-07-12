#include "mili/drivers/comm_wifi.h"
#include "mili/drivers/comm_udp_host.h"

static uint8_t s_wifi_drone_id;

int mili_wifi_init(uint8_t drone_id)
{
    s_wifi_drone_id = drone_id;
#ifdef MILI_HOST_SIM
    return mili_comm_udp_init(drone_id);
#else
    /* TODO: Wi-Fi UDP socket on STM32H7 + LwIP */
    (void)drone_id;
    return 0;
#endif
}

int mili_wifi_send(const uint8_t *data, uint16_t len)
{
#ifdef MILI_HOST_SIM
    return mili_comm_udp_broadcast(data, len);
#else
    (void)data; (void)len; (void)s_wifi_drone_id;
    return -1;
#endif
}

int mili_wifi_recv(uint8_t *data, uint16_t max_len, uint16_t *out_len)
{
#ifdef MILI_HOST_SIM
    return mili_comm_udp_recv(data, max_len, out_len);
#else
    if (out_len) *out_len = 0;
    (void)data; (void)max_len;
    return 0;
#endif
}
