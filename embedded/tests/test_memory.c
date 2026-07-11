#include <assert.h>
#include "mili/memory.h"

int main(void)
{
    assert(mili_memory_within_budget(12, 80, 200));
    assert(!mili_memory_within_budget(1000, 1000, 10000));

    mili_memory_report_t r;
    mili_memory_report(12, 80, 100, &r);
    assert(r.total_bytes <= MILI_FG_MEMORY_BUDGET);
    assert(r.budget_bytes == MILI_FG_MEMORY_BUDGET);
    return 0;
}
