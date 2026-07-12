cmake_minimum_required(VERSION 3.16)
project(mili_vio_embedded C)

set(CMAKE_C_STANDARD 11)

option(MILI_HOST_SIM "Build host simulation" ON)

include_directories(${CMAKE_SOURCE_DIR}/include)

set(MILI_CORE_SRC
    src/core/memory.c
    src/core/profiler.c
    src/core/time.c
    src/core/acceptance.c
    src/core/fc_output.c
    src/hal/dwt.c
    src/hal/dcmi_hal.c
    src/hal/bmi088_hal.c
    src/drivers/bnn_protocol.c
    src/drivers/comm_udp_host.c
    src/drivers/camera_dcmi.c
    src/drivers/imu_bmi088.c
    src/drivers/bnn_spi.c
    src/drivers/comm_uwb.c
    src/drivers/comm_wifi.c
    src/vio/factor_graph.c
    src/vio/g2o_embedded.c
    src/sharing/sharing_embedded.c
    src/pipeline/pipeline.c
    src/rtos/tasks.c
)

if(MILI_HOST_SIM)
    add_executable(mili_host_sim sim/host_main.c ${MILI_CORE_SRC})
    target_compile_definitions(mili_host_sim PRIVATE MILI_HOST_SIM=1)
    target_include_directories(mili_host_sim PRIVATE ${CMAKE_SOURCE_DIR}/include)

    enable_testing()
    add_executable(test_factor_graph tests/test_factor_graph.c src/vio/factor_graph.c src/vio/g2o_embedded.c src/core/memory.c src/core/time.c)
    target_compile_definitions(test_factor_graph PRIVATE MILI_HOST_SIM=1)
    target_include_directories(test_factor_graph PRIVATE ${CMAKE_SOURCE_DIR}/include)
    add_test(NAME factor_graph COMMAND test_factor_graph)

    add_executable(test_memory tests/test_memory.c src/core/memory.c)
    target_include_directories(test_memory PRIVATE ${CMAKE_SOURCE_DIR}/include)
    add_test(NAME memory COMMAND test_memory)

    add_executable(test_pipeline tests/test_pipeline.c ${MILI_CORE_SRC})
    target_compile_definitions(test_pipeline PRIVATE MILI_HOST_SIM=1)
    target_include_directories(test_pipeline PRIVATE ${CMAKE_SOURCE_DIR}/include)
    add_test(NAME pipeline COMMAND test_pipeline)
else()
    add_executable(mili_firmware src/main.c ${MILI_CORE_SRC})
    target_include_directories(mili_firmware PRIVATE ${CMAKE_SOURCE_DIR}/include)
endif()
