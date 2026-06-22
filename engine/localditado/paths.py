"""Default directories per operating system (no external dependencies).

Keeps user data outside the repository and in each OS's idiomatic locations:

- Windows: ``%APPDATA%\\LocalDitado``
- macOS:   ``~/Library/Application Support/LocalDitado``
- Linux:   ``$XDG_CONFIG_HOME/local-ditado`` (default ``~/.config/local-ditado``)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "LocalDitado"
APP_SLUG = "local-ditado"

# Repository/install root (where versioned profiles/ and prompts/ live).
PACKAGE_ROOT = Path(__file__).resolve().parent


def _versioned_root() -> Path:
    """Root containing bundled profiles and prompts."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        root = Path(frozen_root)
        if (root / "profiles").exists() or (root / "prompts").exists():
            return root
    return PACKAGE_ROOT.parent.parent


REPO_ROOT = _versioned_root()


def config_dir() -> Path:
    """User configuration directory (created if needed)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        path = base / APP_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        path = base / APP_SLUG
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> Path:
    """Data directory (history, recordings, logs)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        path = base / APP_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        path = base / APP_SLUG
    path.mkdir(parents=True, exist_ok=True)
    return path


def models_dir() -> Path:
    """Cache for downloaded models (Whisper/Vosk)."""
    path = data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def recordings_dir() -> Path:
    path = data_dir() / "recordings"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return config_dir() / "config.json"


def history_path() -> Path:
    return data_dir() / "history.jsonl"


def log_path() -> Path:
    return data_dir() / "local-ditado.log"


def profiles_dir() -> Path:
    """Versioned profiles in the repository (read-only)."""
    return REPO_ROOT / "profiles"


def prompts_dir() -> Path:
    return REPO_ROOT / "prompts"


def default_prompt_path() -> Path:
    return prompts_dir() / "pt-br-default.txt"
