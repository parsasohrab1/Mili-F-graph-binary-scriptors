/**
 * @file g2o_embedded.h
 * @brief g2o/GTSAM embedded backend integration point
 *
 * Link against g2o_embedded or gtsam_embedded build for STM32H7.
 * This header defines the C wrapper API used by factor_graph.c.
 */
#ifndef MILI_G2O_EMBEDDED_H
#define MILI_G2O_EMBEDDED_H

#include <stdint.h>
#include "mili/types.h"

typedef struct mili_g2o_solver mili_g2o_solver_t;

mili_g2o_solver_t *mili_g2o_create(uint32_t memory_budget);
void mili_g2o_destroy(mili_g2o_solver_t *solver);

int mili_g2o_add_pose(mili_g2o_solver_t *s, uint64_t id, const mili_pose_t *pose, int fixed);
int mili_g2o_add_imu_edge(mili_g2o_solver_t *s, uint64_t i, uint64_t j, const mili_imu_sample_t *imu);
int mili_g2o_add_visual_edge(mili_g2o_solver_t *s, uint64_t pose_id, uint64_t lm_id, float u, float v);
int mili_g2o_optimize(mili_g2o_solver_t *s, uint32_t max_iterations, uint32_t max_ms);
int mili_g2o_get_pose(mili_g2o_solver_t *s, uint64_t id, mili_pose_t *out);

#endif
