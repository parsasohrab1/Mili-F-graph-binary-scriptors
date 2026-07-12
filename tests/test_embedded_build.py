"""Optional embedded build smoke test (skipped if no gcc/cmake)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

EMBEDDED = Path(__file__).resolve().parents[1] / "embedded"


def _has_tool(name: str) -> bool:
    return shutil.which(name) is not None


def test_embedded_build_script_exists() -> None:
    assert (EMBEDDED / "scripts" / "build.ps1").exists()
    assert (EMBEDDED / "CMakeLists.txt").exists()
    assert (EMBEDDED / "src" / "hal" / "dcmi_hal.c").exists()


def test_embedded_quick_build_if_gcc() -> None:
    if not _has_tool("gcc") and not _has_tool("cmake"):
        return
    build_ps1 = EMBEDDED / "scripts" / "build.ps1"
    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(build_ps1), "-Quick"],
        cwd=EMBEDDED,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
