#include "mili/profiler.h"
#include "mili/time.h"
#include <string.h>

static mili_profiler_t g_profiler;
static mili_prof_stage_t g_active = MILI_PROF_COUNT;
static uint64_t g_stage_start_us;

static uint32_t prof_now_us(void)
{
    return (uint32_t)(mili_time_us() & 0xFFFFFFFFU);
}

static uint32_t stage_budget_us(mili_prof_stage_t s)
{
    switch (s) {
    case MILI_PROF_CAMERA:  return 33000U;
    case MILI_PROF_BNN:     return MILI_BUDGET_BNN_MS * 1000U;
    case MILI_PROF_VIO:     return MILI_BUDGET_VIO_MS * 1000U;
    case MILI_PROF_SHARING: return MILI_BUDGET_SHARE_MS * 1000U;
    default: return 0;
    }
}

void mili_profiler_init(mili_profiler_t *prof)
{
    mili_time_init();
    memset(prof, 0, sizeof(*prof));
    for (int i = 0; i < MILI_PROF_COUNT; i++) {
        prof->stages[i].budget_us = stage_budget_us((mili_prof_stage_t)i);
    }
}

void mili_profiler_begin(mili_prof_stage_t stage)
{
    g_active = stage;
    g_stage_start_us = mili_time_us();
}

void mili_profiler_end(mili_prof_stage_t stage)
{
    if (g_active != stage) return;
    uint32_t elapsed = (uint32_t)(mili_time_us() - g_stage_start_us);
    mili_prof_stat_t *s = &g_profiler.stages[stage];
    s->count++;
    s->total_us += elapsed;
    if (elapsed > s->max_us) s->max_us = elapsed;
    if (elapsed > s->budget_us) s->overruns++;
    g_active = MILI_PROF_COUNT;
}

void mili_profiler_tick_second(mili_profiler_t *prof)
{
    prof->uptime_sec++;
}

const mili_prof_stat_t *mili_profiler_get(const mili_profiler_t *prof, mili_prof_stage_t stage)
{
    if (stage >= MILI_PROF_COUNT) return NULL;
    return &prof->stages[stage];
}

uint32_t mili_profiler_bottleneck_stage(const mili_profiler_t *prof)
{
    uint32_t max_avg = 0, stage = 0;
    for (int i = 0; i < MILI_PROF_COUNT; i++) {
        const mili_prof_stat_t *s = &prof->stages[i];
        uint32_t avg = s->count ? s->total_us / s->count : 0;
        if (avg > max_avg) { max_avg = avg; stage = (uint32_t)i; }
    }
    (void)prof;
    return stage;
}

mili_profiler_t *mili_profiler_global(void) { return &g_profiler; }
