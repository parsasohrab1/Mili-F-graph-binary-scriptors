#!/usr/bin/env python3
"""Generate cooperative VIO synthetic dataset."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mili_vio.cli import main

if __name__ == "__main__":
    main()
