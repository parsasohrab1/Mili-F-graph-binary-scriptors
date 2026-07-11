/**
 * @file factor_graph.h
 * @brief Embedded sliding-window factor graph (g2o-compatible API)
 */
#ifndef MILI_FACTOR_GRAPH_H
#define MILI_FACTOR_GRAPH_H

#include "mili/types.h"
#include "mili/memory.h"

typedef struct mili_factor_graph mili_factor_graph_t;

mili_factor_graph_t *mili_fg_create(void);
void mili_fg_destroy(mili_factor_graph_t *fg);

int mili_fg_add_pose(mili_factor_graph_t *fg, uint64_t ts_us,
                     const mili_pose_t *pose, bool fixed);
int mili_fg_add_imu_factor(mili_factor_graph_t *fg, uint16_t i, uint16_t j,
                           const mili_imu_sample_t *imu);
int mili_fg_add_visual(mili_factor_graph_t *fg, uint16_t pose_i,
                       float u, float v);
int mili_fg_add_shared_landmark(mili_factor_graph_t *fg, uint16_t pose_i,
                                const mili_vec3_t *pos, uint32_t global_id);
int mili_fg_add_loop_closure(mili_factor_graph_t *fg, uint16_t i, uint16_t j);

int mili_fg_optimize(mili_factor_graph_t *fg, uint32_t max_ms);
int mili_fg_get_state(mili_factor_graph_t *fg, mili_state_estimate_t *out);
void mili_fg_memory(mili_factor_graph_t *fg, mili_memory_report_t *report);
uint16_t mili_fg_num_poses(const mili_factor_graph_t *fg);

#endif
