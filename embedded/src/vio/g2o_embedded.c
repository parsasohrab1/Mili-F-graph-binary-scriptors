#include "mili/vio/g2o_embedded.h"
#include <stdlib.h>
#include <string.h>

struct mili_g2o_solver {
    uint32_t budget;
    mili_pose_t last_pose;
};

mili_g2o_solver_t *mili_g2o_create(uint32_t memory_budget)
{
    mili_g2o_solver_t *s = calloc(1, sizeof(*s));
    if (s) s->budget = memory_budget;
    return s;
}

void mili_g2o_destroy(mili_g2o_solver_t *solver) { free(solver); }

int mili_g2o_add_pose(mili_g2o_solver_t *s, uint64_t id, const mili_pose_t *pose, int fixed)
{
    (void)id; (void)fixed;
    if (!s || !pose) return -1;
    s->last_pose = *pose;
    return 0;
}

int mili_g2o_add_imu_edge(mili_g2o_solver_t *s, uint64_t i, uint64_t j, const mili_imu_sample_t *imu)
{
    (void)s; (void)i; (void)j; (void)imu;
    return 0;
}

int mili_g2o_add_visual_edge(mili_g2o_solver_t *s, uint64_t pose_id, uint64_t lm_id, float u, float v)
{
    (void)s; (void)pose_id; (void)lm_id; (void)u; (void)v;
    return 0;
}

int mili_g2o_optimize(mili_g2o_solver_t *s, uint32_t max_iterations, uint32_t max_ms)
{
    (void)max_iterations; (void)max_ms;
    return s ? 0 : -1;
}

int mili_g2o_get_pose(mili_g2o_solver_t *s, uint64_t id, mili_pose_t *out)
{
    (void)id;
    if (!s || !out) return -1;
    *out = s->last_pose;
    return 0;
}
