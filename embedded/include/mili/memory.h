/**
 * @file memory.h
 * @brief Memory budget tracking for factor graph (<= 2MB SRS)
 */
#ifndef MILI_MEMORY_H
#define MILI_MEMORY_H

#include <stdint.h>
#include <stdbool.h>
#include "mili_config.h"

typedef struct {
    uint32_t poses_bytes;
    uint32_t landmarks_bytes;
    uint32_t factors_bytes;
    uint32_t total_bytes;
    uint32_t budget_bytes;
    uint16_t num_poses;
    uint16_t num_landmarks;
    uint16_t num_factors;
} mili_memory_report_t;

#define MILI_BYTES_PER_POSE      64U
#define MILI_BYTES_PER_LANDMARK  40U
#define MILI_BYTES_PER_FACTOR    32U

static inline uint32_t mili_memory_estimate(uint16_t poses, uint16_t landmarks, uint16_t factors)
{
    return (uint32_t)poses * MILI_BYTES_PER_POSE
         + (uint32_t)landmarks * MILI_BYTES_PER_LANDMARK
         + (uint32_t)factors * MILI_BYTES_PER_FACTOR;
}

static inline bool mili_memory_within_budget(uint16_t poses, uint16_t landmarks, uint16_t factors)
{
    return mili_memory_estimate(poses, landmarks, factors) <= MILI_FG_MEMORY_BUDGET;
}

void mili_memory_report(uint16_t poses, uint16_t landmarks, uint16_t factors,
                        mili_memory_report_t *out);

#endif /* MILI_MEMORY_H */
