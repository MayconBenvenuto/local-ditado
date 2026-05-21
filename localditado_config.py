"""Compatibility shim: configuration has moved to ``localditado.config`` in ``engine/``.

Re-exports old symbols to avoid breaking existing imports.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "engine"))

from localditado.config import (  # noqa: E402,F401
    DEFAULT_CONFIG_PATH,
    DEFAULT_SETTINGS,
    ensure_config,
    load_settings,
    profile_path,
    read_json,
    write_json,
)
