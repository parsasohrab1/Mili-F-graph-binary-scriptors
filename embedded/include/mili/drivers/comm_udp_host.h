/**
 * @file comm_udp_host.h
 * @brief Host UDP transport for UWB/Wi-Fi driver simulation (MILI_HOST_SIM)
 */
#ifndef MILI_COMM_UDP_HOST_H
#define MILI_COMM_UDP_HOST_H

#include <stdint.h>

#define MILI_COMM_BASE_PORT 7700U
#define MILI_COMM_MAX_DRONES 12U

int mili_comm_udp_init(uint8_t drone_id);
int mili_comm_udp_send_to(uint8_t target_drone, const uint8_t *data, uint16_t len);
int mili_comm_udp_broadcast(const uint8_t *data, uint16_t len);
int mili_comm_udp_recv(uint8_t *data, uint16_t max_len, uint16_t *out_len);
uint32_t mili_comm_udp_bytes_sent(void);
uint32_t mili_comm_udp_last_latency_us(void);
void mili_comm_udp_shutdown(void);

#endif
