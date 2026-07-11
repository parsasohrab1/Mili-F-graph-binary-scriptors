/**
 * @file comm_uwb.h
 * @brief UWB low-latency communication driver
 */
#ifndef MILI_COMM_UWB_H
#define MILI_COMM_UWB_H

#include <stdint.h>

int mili_uwb_init(uint8_t drone_id);
int mili_uwb_send(const uint8_t *data, uint16_t len);
int mili_uwb_recv(uint8_t *data, uint16_t max_len, uint16_t *out_len);
int mili_uwb_broadcast(const uint8_t *data, uint16_t len);

#endif
