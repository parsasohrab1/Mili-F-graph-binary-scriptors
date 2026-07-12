#include "mili/vio/factor_graph.h"
#include "mili/vio/g2o_embedded.h"
#include <stdlib.h>
#include <string.h>

typedef struct {
    mili_pose_t pose;
    uint64_t timestamp_us;
    bool fixed;
} fg_pose_t;

typedef struct {
    mili_vec3_t position;
    uint32_t global_id;
} fg_landmark_t;

struct mili_factor_graph {
    fg_pose_t poses[MILI_FG_MAX_POSES];
    fg_landmark_t landmarks[MILI_FG_MAX_LANDMARKS];
    uint16_t num_poses;
    uint16_t num_landmarks;
    uint16_t num_imu_factors;
    uint16_t num_visual_factors;
    uint16_t num_loop_factors;
    uint32_t landmark_id_next;
    mili_state_estimate_t last_state;
    mili_g2o_solver_t *g2o;
};

static void fg_sync_to_g2o(mili_factor_graph_t *fg)
{
    if (!fg || !fg->g2o) return;
    mili_g2o_clear(fg->g2o);
    for (uint16_t i = 0; i < fg->num_poses; i++) {
        mili_g2o_add_pose(fg->g2o, i, &fg->poses[i].pose, fg->poses[i].fixed ? 1 : 0);
    }
}

mili_factor_graph_t *mili_fg_create(void)
{
    mili_factor_graph_t *fg = calloc(1, sizeof(*fg));
    if (fg) {
        fg->g2o = mili_g2o_create(MILI_FG_MEMORY_BUDGET);
    }
    return fg;
}

void mili_fg_destroy(mili_factor_graph_t *fg)
{
    if (!fg) return;
    if (fg->g2o) mili_g2o_destroy(fg->g2o);
    free(fg);
}

int mili_fg_add_pose(mili_factor_graph_t *fg, uint64_t ts_us,
                     const mili_pose_t *pose, bool fixed)
{
    if (!fg || !pose || fg->num_poses >= MILI_FG_MAX_POSES) return -1;
    if (fg->num_poses >= MILI_FG_MAX_POSES) {
        memmove(&fg->poses[0], &fg->poses[1], (MILI_FG_MAX_POSES - 1) * sizeof(fg_pose_t));
        fg->num_poses = MILI_FG_MAX_POSES - 1;
    }
    fg_pose_t *p = &fg->poses[fg->num_poses++];
    p->pose = *pose;
    p->timestamp_us = ts_us;
    p->fixed = fixed;
    return (int)(fg->num_poses - 1);
}

int mili_fg_add_imu_factor(mili_factor_graph_t *fg, uint16_t i, uint16_t j,
                           const mili_imu_sample_t *imu)
{
    if (!fg || i >= fg->num_poses || j >= fg->num_poses) return -1;
    fg->num_imu_factors++;
    if (fg->g2o) mili_g2o_add_imu_edge(fg->g2o, i, j, imu);
    return 0;
}

int mili_fg_add_visual(mili_factor_graph_t *fg, uint16_t pose_i, float u, float v)
{
    if (!fg || pose_i >= fg->num_poses) return -1;
    uint16_t lm_idx = fg->num_landmarks;
    if (fg->num_landmarks < MILI_FG_MAX_LANDMARKS) {
        fg_landmark_t *lm = &fg->landmarks[fg->num_landmarks++];
        lm->position.x = fg->poses[pose_i].pose.position.x;
        lm->position.y = fg->poses[pose_i].pose.position.y;
        lm->position.z = fg->poses[pose_i].pose.position.z + 3.0f;
        lm->global_id = fg->landmark_id_next++;
    }
    fg->num_visual_factors++;
    if (fg->g2o) mili_g2o_add_visual_edge(fg->g2o, pose_i, lm_idx, u, v);
    return 0;
}

int mili_fg_add_shared_landmark(mili_factor_graph_t *fg, uint16_t pose_i,
                                const mili_vec3_t *pos, uint32_t global_id)
{
    if (!fg || !pos || pose_i >= fg->num_poses) return -1;
    if (fg->num_landmarks >= MILI_FG_MAX_LANDMARKS) return -1;
    fg_landmark_t *lm = &fg->landmarks[fg->num_landmarks++];
    lm->position = *pos;
    lm->global_id = global_id;
    fg->num_visual_factors++;
    if (fg->g2o) {
        mili_g2o_add_visual_edge(fg->g2o, pose_i, (uint64_t)(fg->num_landmarks - 1), 320.0f, 240.0f);
    }
    return 0;
}

int mili_fg_add_loop_closure(mili_factor_graph_t *fg, uint16_t i, uint16_t j)
{
    if (!fg || i >= fg->num_poses || j >= fg->num_poses) return -1;
    fg->num_loop_factors++;
    if (fg->g2o) {
        mili_vec3_t dp = {
            fg->poses[i].pose.position.x - fg->poses[j].pose.position.x,
            fg->poses[i].pose.position.y - fg->poses[j].pose.position.y,
            fg->poses[i].pose.position.z - fg->poses[j].pose.position.z,
        };
        mili_g2o_add_loop_edge(fg->g2o, i, j, &dp);
    }
    return 0;
}

int mili_fg_optimize(mili_factor_graph_t *fg, uint32_t max_ms)
{
    if (!fg || fg->num_poses == 0) return -1;

    fg_sync_to_g2o(fg);

    if (fg->g2o) {
        mili_g2o_optimize(fg->g2o, 4U, max_ms);
        mili_pose_t optimized;
        if (mili_g2o_get_pose(fg->g2o, fg->num_poses - 1, &optimized) == 0) {
            fg->poses[fg->num_poses - 1].pose = optimized;
        }
        fg->last_state.opt_time_us = mili_g2o_last_opt_time_us(fg->g2o);
    } else {
        fg->last_state.opt_time_us = 500U;
    }

    fg_pose_t *last = &fg->poses[fg->num_poses - 1];
    fg->last_state.pose = last->pose;
    fg->last_state.timestamp_us = last->timestamp_us;

    uint16_t factors = fg->num_imu_factors + fg->num_visual_factors + fg->num_loop_factors;
    float unc = 0.5f / (float)(factors + 1);
    fg->last_state.uncertainty = unc;
    for (int i = 0; i < 6; i++) fg->last_state.covariance[i] = unc;
    return 0;
}

int mili_fg_get_state(mili_factor_graph_t *fg, mili_state_estimate_t *out)
{
    if (!fg || !out) return -1;
    *out = fg->last_state;
    return 0;
}

void mili_fg_memory(mili_factor_graph_t *fg, mili_memory_report_t *report)
{
    if (!fg || !report) return;
    uint16_t factors = fg->num_imu_factors + fg->num_visual_factors + fg->num_loop_factors;
    mili_memory_report(fg->num_poses, fg->num_landmarks, factors, report);
    if (fg->g2o) {
        report->total_bytes += mili_g2o_memory_used(fg->g2o);
    }
}

uint16_t mili_fg_num_poses(const mili_factor_graph_t *fg)
{
    return fg ? fg->num_poses : 0;
}

uint32_t mili_fg_last_opt_time_us(const mili_factor_graph_t *fg)
{
    return fg ? fg->last_state.opt_time_us : 0U;
}
