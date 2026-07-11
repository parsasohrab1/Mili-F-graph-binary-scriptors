#include "mili/pipeline.h"
#include "mili/drivers/camera_dcmi.h"
#include "mili/drivers/imu_bmi088.h"
#include "mili/drivers/bnn_spi.h"
#include "mili/drivers/comm_uwb.h"
#include "mili/sharing/sharing_embedded.h"
#include "mili/vio/factor_graph.h"
#include <stdlib.h>
#include <string.h>

#define SHARE_BUF_SIZE 512

struct mili_pipeline {
    uint8_t drone_id;
    mili_factor_graph_t *fg;
    mili_profiler_t prof;
    mili_state_estimate_t state;
    mili_camera_frame_t pending_frame;
    mili_descriptor_frame_t pending_desc;
    uint8_t share_buf[SHARE_BUF_SIZE];
    uint32_t frame_count;
    uint32_t state_updates;
    int running;
};

/* Wire profiler to pipeline instance */
static void prof_sync(mili_pipeline_t *pipe)
{
    mili_profiler_t *g = mili_profiler_global();
    if (g) *g = pipe->prof;
}
static void prof_sync_back(mili_pipeline_t *pipe)
{
    mili_profiler_t *g = mili_profiler_global();
    if (g) pipe->prof = *g;
}

mili_pipeline_t *mili_pipeline_create(uint8_t drone_id)
{
    mili_pipeline_t *p = calloc(1, sizeof(*p));
    if (p) p->drone_id = drone_id;
    return p;
}

void mili_pipeline_destroy(mili_pipeline_t *pipe)
{
    if (!pipe) return;
    if (pipe->fg) mili_fg_destroy(pipe->fg);
    free(pipe);
}

int mili_pipeline_init(mili_pipeline_t *pipe)
{
    if (!pipe) return -1;
    mili_profiler_init(&pipe->prof);
    pipe->fg = mili_fg_create();
    mili_camera_init();
    mili_imu_init();
    mili_bnn_init();
    mili_uwb_init(pipe->drone_id);
    return pipe->fg ? 0 : -1;
}

int mili_pipeline_start(mili_pipeline_t *pipe)
{
    if (!pipe) return -1;
    pipe->running = 1;
    return mili_camera_start(NULL, NULL);
}

void mili_pipeline_stop(mili_pipeline_t *pipe)
{
    if (!pipe) return;
    pipe->running = 0;
    mili_camera_stop();
}

int mili_pipeline_on_frame(mili_pipeline_t *pipe, const mili_camera_frame_t *frame)
{
    if (!pipe || !frame) return -1;
    prof_sync(pipe);
    mili_profiler_begin(MILI_PROF_CAMERA);
    pipe->pending_frame = *frame;
    pipe->frame_count++;
    mili_profiler_end(MILI_PROF_CAMERA);
    prof_sync_back(pipe);
    return mili_pipeline_on_descriptors(pipe, NULL);
}

int mili_pipeline_on_descriptors(mili_pipeline_t *pipe, const mili_descriptor_frame_t *desc)
{
    if (!pipe) return -1;
    prof_sync(pipe);
    mili_profiler_begin(MILI_PROF_BNN);

    if (desc) {
        pipe->pending_desc = *desc;
    } else {
        mili_bnn_extract(&pipe->pending_frame, &pipe->pending_desc);
    }
    mili_profiler_end(MILI_PROF_BNN);
    prof_sync_back(pipe);
    return 0;
}

int mili_pipeline_on_vio_tick(mili_pipeline_t *pipe)
{
    if (!pipe || !pipe->fg) return -1;
    prof_sync(pipe);
    mili_profiler_begin(MILI_PROF_VIO);

    mili_imu_sample_t imu;
    mili_imu_sim_fill(&imu, pipe->pending_frame.timestamp_us);

    mili_pose_t pose = {{0, 0, 0}, {0, 0, 0}};
    uint16_t prev = mili_fg_num_poses(pipe->fg);
    if (prev > 0) {
        pose.position.x = (float)prev * 0.05f;
    }

    mili_fg_add_pose(pipe->fg, pipe->pending_frame.timestamp_us, &pose, prev == 0);

    if (prev > 0) {
        mili_fg_add_imu_factor(pipe->fg, prev - 1, prev, &imu);
    }

    for (uint16_t i = 0; i < pipe->pending_desc.count && i < 5; i++) {
        mili_fg_add_visual(pipe->fg, prev,
            pipe->pending_desc.keypoints[i].u,
            pipe->pending_desc.keypoints[i].v);
    }

    mili_fg_optimize(pipe->fg, MILI_FG_MAX_OPT_MS);
    mili_fg_get_state(pipe->fg, &pipe->state);
    pipe->state_updates++;
    pipe->prof.state_updates = pipe->state_updates;

    mili_profiler_end(MILI_PROF_VIO);
    prof_sync_back(pipe);
    return 0;
}

int mili_pipeline_on_sharing_tick(mili_pipeline_t *pipe)
{
    if (!pipe) return -1;
    prof_sync(pipe);
    mili_profiler_begin(MILI_PROF_SHARING);

    if (mili_share_should_trigger(pipe->state.uncertainty)) {
        mili_share_meta_t meta = {
            .drone_id = pipe->drone_id,
            .timestamp_ns = (uint32_t)pipe->pending_frame.timestamp_us,
            .uncertainty = pipe->state.uncertainty,
            .num_landmarks = 0,
        };
        uint8_t n_lm = pipe->pending_desc.count > 15 ? 15 : (uint8_t)pipe->pending_desc.count;
        uint16_t pkt_len = 0;
        if (mili_share_encode(&meta, pipe->pending_desc.keypoints, n_lm,
                              pipe->share_buf, SHARE_BUF_SIZE, &pkt_len) == 0) {
            mili_uwb_broadcast(pipe->share_buf, pkt_len);
        }
    }

    mili_profiler_end(MILI_PROF_SHARING);
    prof_sync_back(pipe);
    return 0;
}

uint32_t mili_pipeline_state_updates(const mili_pipeline_t *pipe)
{
    return pipe ? pipe->state_updates : 0;
}

void mili_pipeline_memory_report(const mili_pipeline_t *pipe, mili_memory_report_t *out)
{
    if (pipe && pipe->fg && out) mili_fg_memory(pipe->fg, out);
}

const mili_state_estimate_t *mili_pipeline_latest_state(const mili_pipeline_t *pipe)
{
    return pipe ? &pipe->state : NULL;
}

const mili_profiler_t *mili_pipeline_profiler(const mili_pipeline_t *pipe)
{
    return pipe ? &pipe->prof : NULL;
}
