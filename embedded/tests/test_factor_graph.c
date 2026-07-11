#include <assert.h>
#include "mili/vio/factor_graph.h"
#include "mili/memory.h"

int main(void)
{
    mili_factor_graph_t *fg = mili_fg_create();
    assert(fg);

    mili_pose_t pose = {{0, 0, 0}, {0, 0, 0}};
    assert(mili_fg_add_pose(fg, 0, &pose, true) == 0);

    pose.position.x = 0.1f;
    assert(mili_fg_add_pose(fg, 1000, &pose, false) == 1);

    mili_imu_sample_t imu = {{0, 0, 9.81f}, {0, 0, 0}, 500};
    assert(mili_fg_add_imu_factor(fg, 0, 1, &imu) == 0);
    assert(mili_fg_add_visual(fg, 1, 320.0f, 240.0f) == 0);

    assert(mili_fg_optimize(fg, 5) == 0);

    mili_memory_report_t mem;
    mili_fg_memory(fg, &mem);
    assert(mem.total_bytes <= MILI_FG_MEMORY_BUDGET);

    mili_fg_destroy(fg);
    return 0;
}
