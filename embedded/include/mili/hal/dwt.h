/**
 * @file dwt.h
 * @brief DWT cycle counter for STM32H7 profiling
 */
#ifndef MILI_DWT_H
#define MILI_DWT_H

#include <stdint.h>

void mili_dwt_init(void);
uint32_t mili_dwt_cycles(void);
uint32_t mili_dwt_us(void);

#endif
