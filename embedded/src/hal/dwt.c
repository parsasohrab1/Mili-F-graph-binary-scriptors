#include "mili/hal/dwt.h"

#ifndef MILI_HOST_SIM

/* STM32H7 CMSIS — link with device headers in firmware build */
#if defined(__CORTEX_M) || defined(STM32H743xx) || defined(USE_HAL_DRIVER)

#include "core_cm7.h"

#ifndef DWT_CTRL_CYCCNTENA_Msk
#define DWT_CTRL_CYCCNTENA_Msk (1UL << 0)
#endif

extern uint32_t SystemCoreClock;

void mili_dwt_init(void)
{
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
}

uint32_t mili_dwt_cycles(void)
{
    return DWT->CYCCNT;
}

uint32_t mili_dwt_us(void)
{
    if (SystemCoreClock == 0U) return 0U;
    uint64_t us = ((uint64_t)DWT->CYCCNT * 1000000ULL) / (uint64_t)SystemCoreClock;
    return (uint32_t)us;
}

#else

void mili_dwt_init(void) {}
uint32_t mili_dwt_cycles(void) { return 0; }
uint32_t mili_dwt_us(void) { return 0; }

#endif

#else

#include "mili/time.h"

void mili_dwt_init(void) { mili_time_init(); }
uint32_t mili_dwt_cycles(void) { return (uint32_t)mili_time_us(); }
uint32_t mili_dwt_us(void) { return (uint32_t)mili_time_us(); }

#endif
