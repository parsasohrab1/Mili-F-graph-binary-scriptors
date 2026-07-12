/**
 * @file bnn_spi.h
 * @brief BNN chip driver (SPI+DMA) - Product 1
 */
#ifndef MILI_BNN_SPI_H
#define MILI_BNN_SPI_H

#include "mili/types.h"

int mili_bnn_init(void);
int mili_bnn_reset(void);
int mili_bnn_get_version(uint8_t *major, uint8_t *minor, uint8_t *patch);
int mili_bnn_extract(const mili_camera_frame_t *frame, mili_descriptor_frame_t *out);

/* HAL hook — implement with HAL_SPI_TransmitReceive_DMA on STM32H7 */
int mili_bnn_spi_transfer(const uint8_t *tx, uint32_t tx_len,
                          uint8_t *rx, uint32_t rx_cap, uint32_t *rx_len);

#endif
