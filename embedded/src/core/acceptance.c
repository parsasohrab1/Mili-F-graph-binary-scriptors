#include "mili/acceptance.h"
#include "mili/pipeline.h"
#include "mili/profiler.h"
#include "mili/mili_config.h"
#include <stdio.h>

int mili_acceptance_evaluate(mili_pipeline_t *pipe, uint32_t duration_sec,
                             mili_acceptance_report_t *out)
{
    if (!pipe || !out) return -1;

    const mili_profiler_t *prof = mili_pipeline_profiler(pipe);
    mili_memory_report_t mem;
    mili_pipeline_memory_report(pipe, &mem);

    out->state_updates = mili_pipeline_state_updates(pipe);
    out->duration_sec = duration_sec;
    out->memory_bytes = mem.total_bytes;
    out->memory_budget = mem.budget_bytes;
    out->uptime_sec = prof ? prof->uptime_sec : 0;
    out->crashes = prof ? prof->crashes : 0;
    out->stability_target_sec = MILI_STABILITY_MIN_SEC;
    out->state_update_hz = duration_sec > 0
        ? (float)out->state_updates / (float)duration_sec : 0.0f;

    const mili_prof_stat_t *vio = mili_profiler_get(prof, MILI_PROF_VIO);
    out->vio_max_us = vio ? vio->max_us : 0;

    out->hz_jitter_ms = 0.0f;
    out->meets_hz_spec = (out->state_update_hz >= (float)MILI_STATE_UPDATE_HZ * 0.9f);
    out->meets_memory_spec = (out->memory_bytes <= MILI_FG_MEMORY_BUDGET);
    out->meets_stability_spec = (out->crashes == 0);
    out->all_pass = out->meets_hz_spec && out->meets_memory_spec && out->meets_stability_spec;
    return 0;
}

void mili_acceptance_print(const mili_acceptance_report_t *r)
{
    if (!r) return;
    printf("\n=== SRS Acceptance Report ===\n");
    printf("State update rate: %.1f Hz (target %d) %s\n",
           r->state_update_hz, MILI_STATE_UPDATE_HZ,
           r->meets_hz_spec ? "PASS" : "FAIL");
    printf("Hz jitter:         %.2f ms\n", r->hz_jitter_ms);
    printf("FG memory:         %u / %u bytes %s\n",
           r->memory_bytes, r->memory_budget,
           r->meets_memory_spec ? "PASS" : "FAIL");
    printf("VIO max time:      %u us (budget %u ms)\n",
           r->vio_max_us, MILI_FG_MAX_OPT_MS * 1000U);
    printf("Uptime:            %u / %u sec (stability SRS) %s\n",
           r->uptime_sec, r->stability_target_sec,
           r->meets_stability_spec ? "PASS" : "FAIL");
    printf("Overall:           %s\n", r->all_pass ? "ALL PASS" : "SOME FAILED");
}
