# Mili-VIO Embedded Firmware

STM32H7 firmware for cooperative VIO (Phase 5).

## Quick Start (Host Sim)

```bash
cmake -B build -DMILI_HOST_SIM=ON
cmake --build build
./build/mili_host_sim 10
ctest --test-dir build
```

See [docs/PHASE5_EMBEDDED.md](../docs/PHASE5_EMBEDDED.md) for full documentation.
