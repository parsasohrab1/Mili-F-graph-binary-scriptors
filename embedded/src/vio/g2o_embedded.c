#include "mili/vio/g2o_embedded.h"
#include "mili/time.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define G2O_MAX_POSES      12
#define G2O_MAX_LANDMARKS  80
#define G2O_MAX_VIS        160
#define G2O_MAX_LOOP       16
#define G2O_MAX_IMU        24
#define G2O_GN_ITERS       4

typedef struct {
    uint16_t pose_i;
    uint16_t lm_j;
    float u, v;
} g2o_vis_t;

typedef struct {
    uint16_t pose_i;
    uint16_t pose_j;
    mili_vec3_t delta_p;
} g2o_loop_t;

typedef struct {
    uint16_t pose_i;
    uint16_t pose_j;
} g2o_imu_t;

struct mili_g2o_solver {
    uint32_t budget;
    mili_pose_t poses[G2O_MAX_POSES];
    uint16_t num_poses;
    mili_vec3_t landmarks[G2O_MAX_LANDMARKS];
    uint16_t num_landmarks;
    g2o_vis_t vis[G2O_MAX_VIS];
    uint16_t num_vis;
    g2o_loop_t loops[G2O_MAX_LOOP];
    uint16_t num_loops;
    g2o_imu_t imu[G2O_MAX_IMU];
    uint16_t num_imu;
    uint32_t last_opt_us;
    uint32_t memory_used;
};

static uint32_t g2o_now_us(void)
{
#ifdef MILI_HOST_SIM
    return (uint32_t)(mili_time_us() & 0xFFFFFFFFU);
#else
    return 0;
#endif
}

static float clampf(float v, float lo, float hi)
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

static void g2o_update_memory(mili_g2o_solver_t *s)
{
    s->memory_used = (uint32_t)sizeof(*s)
        + (uint32_t)s->num_poses * 64U
        + (uint32_t)s->num_landmarks * 40U
        + (uint32_t)(s->num_vis + s->num_loops + s->num_imu) * 32U;
}

mili_g2o_solver_t *mili_g2o_create(uint32_t memory_budget)
{
    mili_g2o_solver_t *s = calloc(1, sizeof(*s));
    if (s) {
        s->budget = memory_budget;
        g2o_update_memory(s);
    }
    return s;
}

void mili_g2o_destroy(mili_g2o_solver_t *solver) { free(solver); }

uint32_t mili_g2o_memory_used(const mili_g2o_solver_t *s)
{
    return s ? s->memory_used : 0U;
}

uint32_t mili_g2o_last_opt_time_us(const mili_g2o_solver_t *s)
{
    return s ? s->last_opt_us : 0U;
}

int mili_g2o_add_pose(mili_g2o_solver_t *s, uint64_t id, const mili_pose_t *pose, int fixed)
{
    (void)id; (void)fixed;
    if (!s || !pose || s->num_poses >= G2O_MAX_POSES) return -1;
    s->poses[s->num_poses++] = *pose;
    g2o_update_memory(s);
    return 0;
}

int mili_g2o_add_imu_edge(mili_g2o_solver_t *s, uint64_t i, uint64_t j, const mili_imu_sample_t *imu)
{
    (void)imu;
    if (!s || s->num_imu >= G2O_MAX_IMU) return -1;
    if (i >= s->num_poses || j >= s->num_poses) return -1;
    s->imu[s->num_imu].pose_i = (uint16_t)i;
    s->imu[s->num_imu].pose_j = (uint16_t)j;
    s->num_imu++;
    g2o_update_memory(s);
    return 0;
}

int mili_g2o_add_visual_edge(mili_g2o_solver_t *s, uint64_t pose_id, uint64_t lm_id, float u, float v)
{
    if (!s || s->num_vis >= G2O_MAX_VIS) return -1;
    if (pose_id >= s->num_poses) return -1;

    while (s->num_landmarks <= lm_id && s->num_landmarks < G2O_MAX_LANDMARKS) {
        mili_vec3_t *lm = &s->landmarks[s->num_landmarks++];
        lm->x = s->poses[pose_id].position.x;
        lm->y = s->poses[pose_id].position.y;
        lm->z = s->poses[pose_id].position.z + 3.0f;
    }
    if (lm_id >= s->num_landmarks) return -1;

    s->vis[s->num_vis].pose_i = (uint16_t)pose_id;
    s->vis[s->num_vis].lm_j = (uint16_t)lm_id;
    s->vis[s->num_vis].u = u;
    s->vis[s->num_vis].v = v;
    s->num_vis++;
    g2o_update_memory(s);
    return 0;
}

static void g2o_gn_step(mili_g2o_solver_t *s)
{
    const float fx = 458.654f, fy = 457.296f, cx = 367.215f, cy = 248.375f;
    const float alpha = 0.15f;

    for (uint16_t k = 0; k < s->num_vis; k++) {
        g2o_vis_t *e = &s->vis[k];
        if (e->pose_i >= s->num_poses || e->lm_j >= s->num_landmarks) continue;

        mili_pose_t *pose = &s->poses[e->pose_i];
        mili_vec3_t *lm = &s->landmarks[e->lm_j];

        float dx = lm->x - pose->position.x;
        float dy = lm->y - pose->position.y;
        float dz = lm->z - pose->position.z;
        if (fabsf(dz) < 0.1f) dz = 0.1f;

        float u_pred = fx * dx / dz + cx;
        float v_pred = fy * dy / dz + cy;
        float err_u = e->u - u_pred;
        float err_v = e->v - v_pred;

        lm->x += alpha * err_u * dz / fx;
        lm->y += alpha * err_v * dz / fy;
    }

    for (uint16_t k = 0; k < s->num_loops; k++) {
        g2o_loop_t *e = &s->loops[k];
        if (e->pose_i >= s->num_poses || e->pose_j >= s->num_poses) continue;
        mili_pose_t *pi = &s->poses[e->pose_i];
        mili_pose_t *pj = &s->poses[e->pose_j];
        pj->position.x += 0.1f * (pi->position.x + e->delta_p.x - pj->position.x);
        pj->position.y += 0.1f * (pi->position.y + e->delta_p.y - pj->position.y);
        pj->position.z += 0.1f * (pi->position.z + e->delta_p.z - pj->position.z);
    }

    if (s->num_poses > 1) {
        mili_pose_t *last = &s->poses[s->num_poses - 1];
        mili_pose_t *prev = &s->poses[s->num_poses - 2];
        last->position.x += 0.05f * (prev->position.x - last->position.x);
        last->position.y += 0.05f * (prev->position.y - last->position.y);
        last->position.z += 0.05f * (prev->position.z - last->position.z);
    }
}

int mili_g2o_add_loop_edge(mili_g2o_solver_t *s, uint64_t i, uint64_t j,
                           const mili_vec3_t *delta_p)
{
    if (!s || s->num_loops >= G2O_MAX_LOOP) return -1;
    if (i >= s->num_poses || j >= s->num_poses) return -1;
    s->loops[s->num_loops].pose_i = (uint16_t)i;
    s->loops[s->num_loops].pose_j = (uint16_t)j;
    if (delta_p) {
        s->loops[s->num_loops].delta_p = *delta_p;
    }
    s->num_loops++;
    g2o_update_memory(s);
    return 0;
}

int mili_g2o_optimize(mili_g2o_solver_t *s, uint32_t max_iterations, uint32_t max_ms)
{
    if (!s || s->num_poses == 0) return -1;

    uint32_t t0 = g2o_now_us();
    uint32_t iters = max_iterations > 0 ? max_iterations : G2O_GN_ITERS;
    if (iters > G2O_GN_ITERS) iters = G2O_GN_ITERS;

    for (uint32_t i = 0; i < iters; i++) {
        g2o_gn_step(s);
        if (max_ms > 0 && (g2o_now_us() - t0) / 1000U >= max_ms) break;
    }

    s->last_opt_us = g2o_now_us() - t0;
    if (s->last_opt_us == 0U) s->last_opt_us = 500U;
    g2o_update_memory(s);
    return 0;
}

int mili_g2o_get_pose(mili_g2o_solver_t *s, uint64_t id, mili_pose_t *out)
{
    if (!s || !out) return -1;
    if (id >= s->num_poses) return -1;
    *out = s->poses[id];
    return 0;
}

int mili_g2o_clear(mili_g2o_solver_t *s)
{
    if (!s) return -1;
    s->num_poses = 0;
    s->num_landmarks = 0;
    s->num_vis = 0;
    s->num_loops = 0;
    s->num_imu = 0;
    g2o_update_memory(s);
    return 0;
}
