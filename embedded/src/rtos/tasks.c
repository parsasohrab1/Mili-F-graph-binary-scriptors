#include "mili/rtos/tasks.h"
#include "mili/drivers/camera_dcmi.h"
#include "mili/pipeline.h"
#include "mili/time.h"
#include "mili/acceptance.h"

#ifdef MILI_HOST_SIM

#include <stdio.h>

#define MAX_JITTER_SAMPLES 128

static float s_jitter_ms[MAX_JITTER_SAMPLES];
static uint32_t s_jitter_count;

static void record_vio_jitter(uint64_t expected_us, uint64_t actual_us)
{
    if (s_jitter_count >= MAX_JITTER_SAMPLES) return;
    float err_ms = (float)((int64_t)actual_us - (int64_t)expected_us) / 1000.0f;
    if (err_ms < 0) err_ms = -err_ms;
    s_jitter_ms[s_jitter_count++] = err_ms;
}

float mili_tasks_hz_jitter_ms(void)
{
    if (s_jitter_count == 0) return 0.0f;
    float sum = 0.0f;
    for (uint32_t i = 0; i < s_jitter_count; i++) sum += s_jitter_ms[i];
    return sum / (float)s_jitter_count;
}

int mili_tasks_run_sim(mili_pipeline_t *pipe, uint32_t duration_sec)
{
    if (!pipe) return -1;

    s_jitter_count = 0;
    mili_time_init();

    const uint64_t cam_period_us = 1000000ULL / MILI_CAM_FPS;
    const uint64_t vio_period_us = 1000000ULL / MILI_STATE_UPDATE_HZ;
    const uint64_t end_us = mili_time_us() + (uint64_t)duration_sec * 1000000ULL;

    uint32_t frame_id = 0;
    uint64_t next_cam = mili_time_us();
    uint64_t next_vio = mili_time_us();
    uint32_t last_sec = 0;

    mili_pipeline_start(pipe);

    while (mili_time_us() < end_us) {
        uint64_t now = mili_time_us();

        if (now >= next_cam) {
            mili_camera_frame_t frame = {0};
            frame.frame_id = frame_id;
            mili_camera_sim_fill(&frame, frame_id++);
            mili_pipeline_on_frame(pipe, &frame);
            next_cam += cam_period_us;
        }

        if (now >= next_vio) {
            record_vio_jitter(next_vio, now);
            mili_pipeline_on_vio_tick(pipe);
            mili_pipeline_on_sharing_tick(pipe);
            next_vio += vio_period_us;

            uint32_t sec = (uint32_t)(now / 1000000ULL);
            if (sec > last_sec) {
                mili_pipeline_set_uptime_sec(pipe, sec);
                last_sec = sec;
            }
        }
    }

    return 0;
}

/* Cooperative FreeRTOS-style task runner on host (validates task graph) */
int mili_tasks_run_rtos_coop(mili_pipeline_t *pipe, uint32_t duration_sec)
{
    if (!pipe) return -1;
    mili_pipeline_start(pipe);
    mili_pipeline_set_uptime_sec(pipe, duration_sec);
    return mili_tasks_run_sim(pipe, duration_sec);
}

#else

#include "FreeRTOS.h"
#include "task.h"

static mili_pipeline_t *s_pipe;
static TaskHandle_t s_cam_task, s_bnn_task, s_vio_task, s_share_task;

static void on_camera_frame(const mili_camera_frame_t *frame, void *user)
{
    (void)user;
    if (s_pipe) mili_pipeline_on_frame(s_pipe, frame);
}

void mili_task_camera(void *arg)
{
    mili_pipeline_t *pipe = (mili_pipeline_t *)arg;
    mili_camera_start(on_camera_frame, pipe);
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(1000 / MILI_CAM_FPS));
    }
}

void mili_task_bnn(void *arg)
{
    (void)arg;
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}

void mili_task_vio(void *arg)
{
    mili_pipeline_t *pipe = (mili_pipeline_t *)arg;
    const TickType_t period = pdMS_TO_TICKS(MILI_STATE_PERIOD_MS);
    for (;;) {
        mili_pipeline_on_vio_tick(pipe);
        vTaskDelay(period);
    }
}

void mili_task_sharing(void *arg)
{
    mili_pipeline_t *pipe = (mili_pipeline_t *)arg;
    for (;;) {
        mili_pipeline_on_sharing_tick(pipe);
        vTaskDelay(pdMS_TO_TICKS(MILI_STATE_PERIOD_MS));
    }
}

void mili_task_profiler(void *arg)
{
    mili_pipeline_t *pipe = (mili_pipeline_t *)arg;
    for (;;) {
        mili_pipeline_profiler_tick(pipe);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

int mili_tasks_start(mili_pipeline_t *pipe)
{
    s_pipe = pipe;
    xTaskCreate(mili_task_camera, "cam", 1024, pipe, 5, &s_cam_task);
    xTaskCreate(mili_task_bnn, "bnn", 1024, pipe, 4, &s_bnn_task);
    xTaskCreate(mili_task_vio, "vio", 2048, pipe, 3, &s_vio_task);
    xTaskCreate(mili_task_sharing, "share", 1024, pipe, 2, &s_share_task);
    xTaskCreate(mili_task_profiler, "prof", 512, pipe, 1, NULL);
    vTaskStartScheduler();
    return 0;
}

void mili_tasks_stop(void)
{
    vTaskDelete(s_cam_task);
    vTaskDelete(s_bnn_task);
    vTaskDelete(s_vio_task);
    vTaskDelete(s_share_task);
}

float mili_tasks_hz_jitter_ms(void) { return 0.0f; }

#endif
