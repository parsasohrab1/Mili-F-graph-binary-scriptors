#include "mili/memory.h"

void mili_memory_report(uint16_t poses, uint16_t landmarks, uint16_t factors,
                        mili_memory_report_t *out)
{
    if (!out) return;
    out->poses_bytes = (uint32_t)poses * MILI_BYTES_PER_POSE;
    out->landmarks_bytes = (uint32_t)landmarks * MILI_BYTES_PER_LANDMARK;
    out->factors_bytes = (uint32_t)factors * MILI_BYTES_PER_FACTOR;
    out->total_bytes = out->poses_bytes + out->landmarks_bytes + out->factors_bytes;
    out->budget_bytes = MILI_FG_MEMORY_BUDGET;
    out->num_poses = poses;
    out->num_landmarks = landmarks;
    out->num_factors = factors;
}
