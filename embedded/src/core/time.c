#include "mili/time.h"

#ifdef MILI_HOST_SIM

#if defined(_WIN32)
#include <windows.h>
static LARGE_INTEGER s_freq;
static LARGE_INTEGER s_start;
#else
#include <time.h>
#endif

void mili_time_init(void)
{
#if defined(_WIN32)
    QueryPerformanceFrequency(&s_freq);
    QueryPerformanceCounter(&s_start);
#else
    /* no-op */
#endif
}

uint64_t mili_time_us(void)
{
#if defined(_WIN32)
    LARGE_INTEGER now;
    QueryPerformanceCounter(&now);
    return (uint64_t)((now.QuadPart - s_start.QuadPart) * 1000000ULL / (uint64_t)s_freq.QuadPart);
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000ULL + (uint64_t)ts.tv_nsec / 1000ULL;
#endif
}

#else /* STM32H7 */

/* Uses DWT cycle counter when available */
#include "mili/hal/dwt.h"

void mili_time_init(void)
{
    mili_dwt_init();
}

uint64_t mili_time_us(void)
{
    return mili_dwt_us();
}

#endif

uint32_t mili_time_ms(void)
{
    return (uint32_t)(mili_time_us() / 1000ULL);
}
