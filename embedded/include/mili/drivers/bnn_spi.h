/**
 * @file bnn_spi.h
 * @brief BNN chip driver (SPI+DMA) - Product 1
 */
#ifndef MILI_BNN_SPI_H
#define MILI_BNN_SPI_H

#include "mili/types.h"

int mili_bnn_init(void);
int mili_bnn_reset(void);
int mili_bnn_extract(const mili_camera_frame_t *frame, mili_descriptor_frame_t *out);

#endif
