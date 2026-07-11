/**
 * @file profiler.h
 * @brief Pipeline profiling and bottleneck detection
 */
#ifndef MILI_PROFILER_H
#define MILI_PROFILER_H

#include <stdint.h>
#include "mili_config.h"

typedef enum {
    MILI_PROF_CAMERA = 0,
    MILI_PROF_BNN,
    MILI_PROF_VIO,
    MILI_PROF_SHARING,
    MILI_PROF_COUNT
} mili_prof_stage_t;

typedef struct {
    uint32_t count;
    uint32_t total_us;
    uint32_t max_us;
    uint32_t budget_us;
    uint32_t overruns;
} mili_prof_stat_t;

typedef struct {
    mili_prof_stat_t stages[MILI_PROF_COUNT];
    uint32_t state_updates;
    uint32_t uptime_sec;
    uint32_t crashes;
} mili_profiler_t;

void mili_profiler_init(mili_profiler_t *prof);
void mili_profiler_begin(mili_prof_stage_t stage);
void mili_profiler_end(mili_prof_stage_t stage);
void mili_profiler_tick_second(mili_profiler_t *prof);
const mili_prof_stat_t *mili_profiler_get(const mili_profiler_t *prof, mili_prof_stage_t stage);
uint32_t mili_profiler_bottleneck_stage(const mili_profiler_t *prof);

/* Global profiler used by pipeline stages */
mili_profiler_t *mili_profiler_global(void);

#endif /* MILI_PROFILER_H */
