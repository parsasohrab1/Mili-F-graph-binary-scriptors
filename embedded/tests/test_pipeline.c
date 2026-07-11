#include <assert.h>
#include "mili/pipeline.h"
#include "mili/memory.h"
#include "mili/rtos/tasks.h"

int main(void)
{
    mili_pipeline_t *pipe = mili_pipeline_create(0);
    assert(pipe);
    assert(mili_pipeline_init(pipe) == 0);

    mili_pipeline_start(pipe);
    assert(mili_tasks_run_sim(pipe, 5) == 0);
    assert(mili_pipeline_state_updates(pipe) >= 90);

    mili_memory_report_t mem;
    mili_pipeline_memory_report(pipe, &mem);
    assert(mem.total_bytes <= MILI_FG_MEMORY_BUDGET);

    mili_pipeline_destroy(pipe);
    return 0;
}
