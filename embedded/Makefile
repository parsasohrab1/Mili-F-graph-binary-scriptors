# Host simulation build (gcc or MSVC)

CC ?= gcc
CFLAGS = -std=c11 -Wall -Wextra -Iinclude -DMILI_HOST_SIM=1
LDFLAGS =

HAL_SRC = src/hal/dwt.c src/hal/dcmi_hal.c src/hal/bmi088_hal.c
CORE_SRC = src/core/memory.c src/core/profiler.c src/core/time.c src/core/acceptance.c src/core/fc_output.c

SRC = $(CORE_SRC) $(HAL_SRC) \
      src/drivers/bnn_protocol.c src/drivers/comm_udp_host.c \
      src/drivers/camera_dcmi.c src/drivers/imu_bmi088.c \
      src/drivers/bnn_spi.c src/drivers/comm_uwb.c src/drivers/comm_wifi.c \
      src/vio/factor_graph.c src/vio/g2o_embedded.c \
      src/sharing/sharing_embedded.c src/pipeline/pipeline.c src/rtos/tasks.c

.PHONY: all sim test quick acceptance clean

all: build/mili_host_sim build/test_factor_graph build/test_memory build/test_pipeline

sim: build/mili_host_sim
	build\mili_host_sim.exe 10

quick: build/mili_host_sim
	build\mili_host_sim.exe --quick

acceptance: build/mili_host_sim
	build\mili_host_sim.exe 30

build/mili_host_sim: sim/host_main.c $(SRC)
	@if not exist build mkdir build
	$(CC) $(CFLAGS) -o $@ sim/host_main.c $(SRC) $(LDFLAGS)

build/test_factor_graph: tests/test_factor_graph.c src/vio/factor_graph.c src/vio/g2o_embedded.c src/core/memory.c
	@if not exist build mkdir build
	$(CC) $(CFLAGS) -o $@ tests/test_factor_graph.c src/vio/factor_graph.c src/vio/g2o_embedded.c src/core/memory.c

build/test_memory: tests/test_memory.c src/core/memory.c
	@if not exist build mkdir build
	$(CC) $(CFLAGS) -o $@ tests/test_memory.c src/core/memory.c

build/test_pipeline: tests/test_pipeline.c $(SRC)
	@if not exist build mkdir build
	$(CC) $(CFLAGS) -o $@ tests/test_pipeline.c $(SRC)

clean:
	@if exist build rmdir /s /q build
