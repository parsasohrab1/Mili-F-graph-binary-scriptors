/**
 * @file host_main.c
 * @brief Desktop host simulation of embedded pipeline
 */
#define MILI_HOST_SIM 1

#include <stdio.h>
#include <stdlib.h>
#include "mili/pipeline.h"
#include "mili/rtos/tasks.h"
#include "mili/memory.h"

static int run_acceptance(mili_pipeline_t *pipe, uint32_t duration_sec)
{
    int pass = 1;
    const mili_profiler_t *prof = mili_pipeline_profiler(pipe);
    mili_memory_report_t mem;
    mili_pipeline_memory_report(pipe, &mem);

    float update_hz = (float)mili_pipeline_state_updates(pipe) / (float)duration_sec;
    printf("\n=== Acceptance Report ===\n");
    printf("State update rate: %.1f Hz (target %d) %s\n",
           update_hz, MILI_STATE_UPDATE_HZ,
           update_hz >= 18.0f ? "PASS" : "FAIL");
    if (update_hz < 18.0f) pass = 0;

    printf("FG memory: %u / %u bytes %s\n",
           mem.total_bytes, mem.budget_bytes,
           mem.total_bytes <= MILI_FG_MEMORY_BUDGET ? "PASS" : "FAIL");
    if (mem.total_bytes > MILI_FG_MEMORY_BUDGET) pass = 0;

    printf("Uptime: %u sec (stability target %u) %s\n",
           prof->uptime_sec, duration_sec,
           prof->crashes == 0 ? "PASS" : "FAIL");
    if (prof->crashes > 0) pass = 0;

    printf("Bottleneck stage: %u\n", mili_profiler_bottleneck_stage(prof));

    for (int i = 0; i < MILI_PROF_COUNT; i++) {
        const mili_prof_stat_t *s = mili_profiler_get(prof, (mili_prof_stage_t)i);
        if (s && s->count) {
            printf("  Stage %d: avg=%u us max=%u us overruns=%u\n",
                   i, s->total_us / s->count, s->max_us, s->overruns);
        }
    }

    return pass;
}

int main(int argc, char **argv)
{
    uint32_t duration = 10;
    if (argc > 1) duration = (uint32_t)atoi(argv[1]);

    printf("Mili-VIO Embedded Host Simulator\n");
    printf("Duration: %u sec | Target: %d Hz\n", duration, MILI_STATE_UPDATE_HZ);

    mili_pipeline_t *pipe = mili_pipeline_create(0);
    mili_pipeline_init(pipe);
    mili_tasks_run_sim(pipe, duration);

    int ok = run_acceptance(pipe, duration);
    mili_pipeline_destroy(pipe);

    return ok ? 0 : 1;
}
