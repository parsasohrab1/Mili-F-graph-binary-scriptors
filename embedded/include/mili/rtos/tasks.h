/**
 * @file tasks.h
 * @brief FreeRTOS task definitions: camera -> BNN -> VIO -> sharing
 */
#ifndef MILI_TASKS_H
#define MILI_TASKS_H

#include "mili/pipeline.h"

#ifdef MILI_HOST_SIM
/* Host simulation - no FreeRTOS */
int mili_tasks_run_sim(mili_pipeline_t *pipe, uint32_t duration_sec);
#else
#include "FreeRTOS.h"
#include "task.h"

void mili_task_camera(void *arg);
void mili_task_bnn(void *arg);
void mili_task_vio(void *arg);
void mili_task_sharing(void *arg);
void mili_task_profiler(void *arg);

int mili_tasks_start(mili_pipeline_t *pipe);
void mili_tasks_stop(void);
#endif

#endif
