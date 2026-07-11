/**
 * @file pipeline.h
 * @brief Real-time VIO pipeline orchestrator (20Hz)
 */
#ifndef MILI_PIPELINE_H
#define MILI_PIPELINE_H

#include "mili/types.h"
#include "mili/profiler.h"
#include "mili/memory.h"

typedef struct mili_pipeline mili_pipeline_t;

mili_pipeline_t *mili_pipeline_create(uint8_t drone_id);
void mili_pipeline_destroy(mili_pipeline_t *pipe);

int mili_pipeline_init(mili_pipeline_t *pipe);
int mili_pipeline_start(mili_pipeline_t *pipe);
void mili_pipeline_stop(mili_pipeline_t *pipe);

/* Stage handlers called from RTOS tasks */
int mili_pipeline_on_frame(mili_pipeline_t *pipe, const mili_camera_frame_t *frame);
int mili_pipeline_on_descriptors(mili_pipeline_t *pipe, const mili_descriptor_frame_t *desc);
int mili_pipeline_on_vio_tick(mili_pipeline_t *pipe);
int mili_pipeline_on_sharing_tick(mili_pipeline_t *pipe);

const mili_state_estimate_t *mili_pipeline_latest_state(const mili_pipeline_t *pipe);
const mili_profiler_t *mili_pipeline_profiler(const mili_pipeline_t *pipe);
uint32_t mili_pipeline_state_updates(const mili_pipeline_t *pipe);
void mili_pipeline_memory_report(const mili_pipeline_t *pipe, mili_memory_report_t *out);

#endif
