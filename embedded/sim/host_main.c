/**
 * @file host_main.c
 * @brief Desktop host simulation of embedded pipeline
 */
#define MILI_HOST_SIM 1

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mili/pipeline.h"
#include "mili/rtos/tasks.h"
#include "mili/acceptance.h"
#include "mili/mili_config.h"

static void usage(const char *prog)
{
    printf("Usage: %s [duration_sec] [--stability] [--rtos-coop]\n", prog);
    printf("  duration_sec  Simulation length (default 10)\n");
    printf("  --stability   Run 1-hour SRS stability test (%u sec)\n", MILI_STABILITY_MIN_SEC);
    printf("  --quick       30-second acceptance (default for CI)\n");
    printf("  --rtos-coop   Run cooperative FreeRTOS task graph on host\n");
}

int main(int argc, char **argv)
{
    uint32_t duration = 10;
    int rtos_coop = 0;
    int stability = 0;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--stability") == 0) {
            stability = 1;
            duration = MILI_STABILITY_MIN_SEC;
        } else if (strcmp(argv[i], "--quick") == 0) {
            duration = 30;
        } else if (strcmp(argv[i], "--rtos-coop") == 0) {
            rtos_coop = 1;
        } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            duration = (uint32_t)atoi(argv[i]);
        }
    }

    if (stability) {
        printf("WARNING: 1-hour stability test — use --quick for CI\n");
    }

    printf("Mili-VIO Embedded Host Simulator\n");
    printf("Duration: %u sec | Target: %d Hz | Mode: %s\n",
           duration, MILI_STATE_UPDATE_HZ,
           rtos_coop ? "FreeRTOS-coop" : "timed-sim");

    mili_pipeline_t *pipe = mili_pipeline_create(0);
    mili_pipeline_init(pipe);

    if (rtos_coop) {
        mili_tasks_run_rtos_coop(pipe, duration);
    } else {
        mili_tasks_run_sim(pipe, duration);
    }

    mili_acceptance_report_t report;
    mili_acceptance_evaluate(pipe, duration, &report);
    report.hz_jitter_ms = mili_tasks_hz_jitter_ms();
    mili_acceptance_print(&report);

    const mili_profiler_t *prof = mili_pipeline_profiler(pipe);
    printf("Bottleneck stage: %u\n", mili_profiler_bottleneck_stage(prof));
    for (int i = 0; i < MILI_PROF_COUNT; i++) {
        const mili_prof_stat_t *s = mili_profiler_get(prof, (mili_prof_stage_t)i);
        if (s && s->count) {
            printf("  Stage %d: avg=%u us max=%u us overruns=%u\n",
                   i, s->total_us / s->count, s->max_us, s->overruns);
        }
    }

    int ok = report.all_pass;
    mili_pipeline_destroy(pipe);
    return ok ? 0 : 1;
}
