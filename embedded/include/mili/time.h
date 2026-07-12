/**
 * @file time.h
 * @brief High-resolution monotonic time (host + STM32)
 */
#ifndef MILI_TIME_H
#define MILI_TIME_H

#include <stdint.h>

void mili_time_init(void);
uint64_t mili_time_us(void);
uint32_t mili_time_ms(void);

#endif
