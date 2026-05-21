"""Transcription history as JSONL (one line per dictation).

Stored in the user data directory. Can be disabled for privacy
(``save_transcript: false``).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import paths


def append_entry(text: str, meta: dict | None = None, path: Path | None = None) -> None:
    if not text.strip():
        return
    path = path or paths.history_path()
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "text": text.strip(),
        **(meta or {}),
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_history(limit: int = 100, path: Path | None = None) -> list[dict]:
    path = path or paths.history_path()
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[dict] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    out.reverse()  # most recent first
    return out


def clear_history(path: Path | None = None) -> None:
    path = path or paths.history_path()
    path.unlink(missing_ok=True)
