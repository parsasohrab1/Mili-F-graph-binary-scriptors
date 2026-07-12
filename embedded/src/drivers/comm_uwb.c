#include "mili/drivers/comm_uwb.h"
#include "mili/drivers/comm_udp_host.h"
#include <string.h>

static uint8_t s_drone_id;

int mili_uwb_init(uint8_t drone_id)
{
    s_drone_id = drone_id;
#ifdef MILI_HOST_SIM
    return mili_comm_udp_init(drone_id);
#else
    /* TODO: UWB module AT init (Decawave/Qorvo) */
    (void)drone_id;
    return 0;
#endif
}

int mili_uwb_send(const uint8_t *data, uint16_t len)
{
    if (!data || len == 0) return -1;
#ifdef MILI_HOST_SIM
    return mili_comm_udp_broadcast(data, len);
#else
  (void)s_drone_id;
    return -1;
#endif
}

int mili_uwb_recv(uint8_t *data, uint16_t max_len, uint16_t *out_len)
{
#ifdef MILI_HOST_SIM
    return mili_comm_udp_recv(data, max_len, out_len);
#else
    if (out_len) *out_len = 0;
    (void)data; (void)max_len;
    return 0;
#endif
}

int mili_uwb_broadcast(const uint8_t *data, uint16_t len)
{
    return mili_uwb_send(data, len);
}

uint32_t mili_uwb_bytes_sent(void)
{
#ifdef MILI_HOST_SIM
    return mili_comm_udp_bytes_sent();
#else
    return 0;
#endif
}

uint32_t mili_uwb_last_latency_us(void)
{
#ifdef MILI_HOST_SIM
    return mili_comm_udp_last_latency_us();
#else
    return 0;
#endif
}
