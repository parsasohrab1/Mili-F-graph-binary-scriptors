# Simple Makefile for host simulation (no CMake required)
CC ?= gcc
CFLAGS = -std=c11 -Wall -Iinclude -DMILI_HOST_SIM=1
LDFLAGS =

SRC = src/core/memory.c src/core/profiler.c \
      src/drivers/camera_dcmi.c src/drivers/imu_bmi088.c \
      src/drivers/bnn_spi.c src/drivers/comm_uwb.c src/drivers/comm_wifi.c \
      src/vio/factor_graph.c src/vio/g2o_embedded.c \
      src/sharing/sharing_embedded.c src/pipeline/pipeline.c src/rtos/tasks.c

.PHONY: all sim test clean

all: sim test_factor_graph test_memory test_pipeline

sim: build/mili_host_sim
	./build/mili_host_sim 5

build/mili_host_sim: sim/host_main.c $(SRC)
	@mkdir -p build
	$(CC) $(CFLAGS) -o $@ sim/host_main.c $(SRC) $(LDFLAGS)

test_factor_graph: build/test_factor_graph
	./build/test_factor_graph

build/test_factor_graph: tests/test_factor_graph.c src/vio/factor_graph.c src/core/memory.c
	@mkdir -p build
	$(CC) $(CFLAGS) -o $@ tests/test_factor_graph.c src/vio/factor_graph.c src/core/memory.c

test_memory: build/test_memory
	./build/test_memory

build/test_memory: tests/test_memory.c src/core/memory.c
	@mkdir -p build
	$(CC) $(CFLAGS) -o $@ tests/test_memory.c src/core/memory.c

test_pipeline: build/test_pipeline
	./build/test_pipeline

build/test_pipeline: tests/test_pipeline.c $(SRC)
	@mkdir -p build
	$(CC) $(CFLAGS) -o $@ tests/test_pipeline.c $(SRC)

clean:
	rm -rf build
