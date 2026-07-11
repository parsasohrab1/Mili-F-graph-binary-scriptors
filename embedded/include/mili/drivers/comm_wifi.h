/**
 * @file comm_wifi.h
 * @brief Wi-Fi fallback communication driver
 */
#ifndef MILI_COMM_WIFI_H
#define MILI_COMM_WIFI_H

#include <stdint.h>

int mili_wifi_init(uint8_t drone_id);
int mili_wifi_send(const uint8_t *data, uint16_t len);
int mili_wifi_recv(uint8_t *data, uint16_t max_len, uint16_t *out_len);

#endif
