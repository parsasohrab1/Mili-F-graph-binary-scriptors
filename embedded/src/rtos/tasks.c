#include "mili/rtos/tasks.h"
#include "mili/drivers/camera_dcmi.h"
#include "mili/pipeline.h"

#ifdef MILI_HOST_SIM

#include <stdio.h>

uint32_t mili_host_time_us(void)
{
    static uint32_t t;
    return t += 1000;
}

int mili_tasks_run_sim(mili_pipeline_t *pipe, uint32_t duration_sec)
{
    if (!pipe) return -1;

    const uint32_t cam_period_ms = 1000 / MILI_CAM_FPS;
    const uint32_t vio_period_ms = MILI_STATE_PERIOD_MS;
    uint32_t elapsed_ms = 0;
    uint32_t frame_id = 0;
    uint32_t next_cam = 0, next_vio = 0;

    mili_pipeline_start(pipe);

    while (elapsed_ms < duration_sec * 1000U) {
        if (elapsed_ms >= next_cam) {
            mili_camera_frame_t frame = {0};
            mili_camera_sim_fill(&frame, frame_id++);
            mili_pipeline_on_frame(pipe, &frame);
            next_cam += cam_period_ms;
        }

        if (elapsed_ms >= next_vio) {
            mili_pipeline_on_vio_tick(pipe);
            mili_pipeline_on_sharing_tick(pipe);
            pipe->prof.uptime_sec = elapsed_ms / 1000U;
            next_vio += vio_period_ms;
        }

        elapsed_ms += 1;
    }

    return 0;
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
        mili_profiler_tick_second(&pipe->prof);
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

#endif
