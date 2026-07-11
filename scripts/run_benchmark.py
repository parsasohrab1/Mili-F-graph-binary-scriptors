#!/usr/bin/env python3
"""Run Phase 1 VIO benchmark."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mili_vio.benchmark.cli import main

if __name__ == "__main__":
    main()
