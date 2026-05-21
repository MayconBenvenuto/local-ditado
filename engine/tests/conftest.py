"""Ensures the ``localditado`` package (in engine/) is importable from tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
