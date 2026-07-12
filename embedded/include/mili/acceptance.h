/**
 * @file acceptance.h
 * @brief SRS acceptance metrics for embedded pipeline
 */
#ifndef MILI_ACCEPTANCE_H
#define MILI_ACCEPTANCE_H

#include <stdint.h>
#include "mili_config.h"

struct mili_pipeline;
typedef struct mili_pipeline mili_pipeline_t;

typedef struct {
    float state_update_hz;
    float hz_jitter_ms;
    uint32_t state_updates;
    uint32_t duration_sec;
    uint32_t memory_bytes;
    uint32_t memory_budget;
    uint32_t uptime_sec;
    uint32_t crashes;
    uint32_t vio_max_us;
    uint32_t stability_target_sec;
    int meets_hz_spec;
    int meets_memory_spec;
    int meets_stability_spec;
    int all_pass;
} mili_acceptance_report_t;

int mili_acceptance_evaluate(mili_pipeline_t *pipe, uint32_t duration_sec,
                             mili_acceptance_report_t *out);
void mili_acceptance_print(const mili_acceptance_report_t *r);

#endif
