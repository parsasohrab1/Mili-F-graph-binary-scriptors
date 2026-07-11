/**
 * @file main.c
 * @brief STM32H7 firmware entry point (FreeRTOS)
 */
#include "mili/pipeline.h"
#include "mili/rtos/tasks.h"

int main(void)
{
    /* HAL_Init(); SystemClock_Config(); MX_GPIO_Init(); ... */

    mili_pipeline_t *pipe = mili_pipeline_create(0);
    mili_pipeline_init(pipe);
    mili_tasks_start(pipe); /* does not return */

    for (;;) {}
    return 0;
}
