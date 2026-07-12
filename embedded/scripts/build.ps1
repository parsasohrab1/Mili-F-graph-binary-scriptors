# Build embedded host simulator on Windows
param(
    [switch]$Quick,
    [switch]$Acceptance,
    [switch]$Test,
    [int]$Duration = 10
)

$ErrorActionPreference = "Stop"
$EmbeddedRoot = Split-Path $PSScriptRoot -Parent
Set-Location $EmbeddedRoot

function Find-Gcc {
    $candidates = @(
        "gcc",
        "C:\msys64\mingw64\bin\gcc.exe",
        "C:\msys64\ucrt64\bin\gcc.exe",
        "C:\MinGW\bin\gcc.exe",
        "C:\Program Files\Git\usr\bin\gcc.exe"
    )
    foreach ($c in $candidates) {
        if (Get-Command $c -ErrorAction SilentlyContinue) { return $c }
        if (Test-Path $c) { return $c }
    }
    return $null
}

function Find-Cmake {
    $candidates = @("cmake", "C:\Program Files\CMake\bin\cmake.exe")
    foreach ($c in $candidates) {
        if (Get-Command $c -ErrorAction SilentlyContinue) { return $c }
        if (Test-Path $c) { return $c }
    }
    return $null
}

$gcc = Find-Gcc
$cmake = Find-Cmake

Write-Host "=== Mili Embedded Build ===" -ForegroundColor Cyan

if ($cmake) {
    Write-Host "Using CMake: $cmake"
    & $cmake -B build -DMILI_HOST_SIM=ON
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $cmake --build build --config Release
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $sim = Join-Path $EmbeddedRoot "build\mili_host_sim.exe"
    if (-not (Test-Path $sim)) { $sim = Join-Path $EmbeddedRoot "build\Release\mili_host_sim.exe" }
} elseif ($gcc) {
    Write-Host "Using GCC: $gcc"
    $env:CC = $gcc
    & mingw32-make all 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $gcc -std=c11 -Wall -Iinclude -DMILI_HOST_SIM=1 -o build/mili_host_sim.exe `
            sim/host_main.c `
            src/core/memory.c src/core/profiler.c src/core/time.c src/core/acceptance.c src/core/fc_output.c `
            src/hal/dwt.c src/hal/dcmi_hal.c src/hal/bmi088_hal.c `
            src/drivers/bnn_protocol.c src/drivers/comm_udp_host.c `
            src/drivers/camera_dcmi.c src/drivers/imu_bmi088.c src/drivers/bnn_spi.c `
            src/drivers/comm_uwb.c src/drivers/comm_wifi.c `
            src/vio/factor_graph.c src/vio/g2o_embedded.c `
            src/sharing/sharing_embedded.c src/pipeline/pipeline.c src/rtos/tasks.c
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    $sim = Join-Path $EmbeddedRoot "build\mili_host_sim.exe"
} else {
    Write-Host "ERROR: No gcc or cmake found." -ForegroundColor Red
    Write-Host "Install MSYS2: winget install MSYS2.MSYS2"
    Write-Host "Then: pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-cmake make"
    exit 1
}

if (-not (Test-Path $sim)) {
    Write-Host "ERROR: Build succeeded but simulator not found at $sim" -ForegroundColor Red
    exit 1
}

Write-Host "Build OK: $sim" -ForegroundColor Green

if ($Test) {
    Write-Host "=== CTest ===" -ForegroundColor Cyan
    & $cmake --test-dir (Join-Path $EmbeddedRoot "build") -C Release --output-on-failure
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "CTest OK" -ForegroundColor Green
}

if ($Quick) {
    & $sim --quick
} elseif ($Acceptance) {
    & $sim 30
} elseif ($Duration -gt 0) {
    & $sim $Duration
}
exit $LASTEXITCODE
