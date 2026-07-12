"""Embedded C build + CTest + host acceptance runner."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class EmbeddedValidationReport:
    cmake_available: bool
    build_ok: bool
    ctest_ok: bool
    acceptance_ok: bool
    acceptance_stdout: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def all_pass(self) -> bool:
        return self.build_ok and self.ctest_ok and self.acceptance_ok


def _repo_embedded_root() -> Path:
    return Path(__file__).resolve().parents[3] / "embedded"


def run_embedded_validation(
    quick: bool = True,
    embedded_root: Optional[Path] = None,
) -> EmbeddedValidationReport:
    """
    Build embedded host sim, run CTest, and run acceptance (--quick = 30s).

    Requires cmake on PATH (MSVC or gcc). Skips gracefully when unavailable.
    """
    root = embedded_root or _repo_embedded_root()
    cmake = shutil.which("cmake")
    notes: list[str] = []

    if not cmake:
        return EmbeddedValidationReport(
            cmake_available=False,
            build_ok=False,
            ctest_ok=False,
            acceptance_ok=False,
            notes=["cmake not on PATH — embedded validation skipped"],
        )

    build_dir = root / "build"
    try:
        subprocess.run(
            [cmake, "-B", str(build_dir), "-DMILI_HOST_SIM=ON"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [cmake, "--build", str(build_dir), "--config", "Release"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        build_ok = True
    except subprocess.CalledProcessError as exc:
        notes.append(f"Embedded build failed: {exc.stderr or exc.stdout}")
        return EmbeddedValidationReport(
            cmake_available=True,
            build_ok=False,
            ctest_ok=False,
            acceptance_ok=False,
            notes=notes,
        )

    ctest_ok = False
    try:
        result = subprocess.run(
            [cmake, "--test-dir", str(build_dir), "-C", "Release", "--output-on-failure"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        ctest_ok = result.returncode == 0
        if not ctest_ok:
            notes.append(f"CTest failed:\n{result.stdout}\n{result.stderr}")
    except subprocess.CalledProcessError as exc:
        notes.append(f"CTest error: {exc}")

    sim_candidates = [
        build_dir / "Release" / "mili_host_sim.exe",
        build_dir / "mili_host_sim.exe",
        build_dir / "Release" / "mili_host_sim",
        build_dir / "mili_host_sim",
    ]
    sim = next((p for p in sim_candidates if p.exists()), None)
    acceptance_ok = False
    stdout = ""
    if sim:
        args = ["--quick"] if quick else ["30"]
        try:
            result = subprocess.run(
                [str(sim), *args],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=120 if quick else 600,
            )
            stdout = result.stdout
            acceptance_ok = result.returncode == 0
            if not acceptance_ok:
                notes.append("Host sim acceptance returned non-zero exit code")
        except subprocess.TimeoutExpired:
            notes.append("Host sim acceptance timed out")
    else:
        notes.append("mili_host_sim binary not found after build")

    if build_ok and ctest_ok and acceptance_ok:
        notes.append("Embedded build + CTest + acceptance PASS")

    return EmbeddedValidationReport(
        cmake_available=True,
        build_ok=build_ok,
        ctest_ok=ctest_ok,
        acceptance_ok=acceptance_ok,
        acceptance_stdout=stdout,
        notes=notes,
    )
