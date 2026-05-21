"""Cross-platform global hotkey via pynput.

Accepts friendly strings like ``"ctrl+alt+d"`` and converts them to pynput format
(``"<ctrl>+<alt>+d"``). Works on Windows, macOS, and Linux/X11.

Known caveats:
- **Wayland (Linux)**: global hotkeys are limited; run in an X11 session or register
  the shortcut in the desktop environment pointing to ``local-ditado once``.
- **macOS**: requires Accessibility permission for the app that registers the hotkey.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

log = logging.getLogger("localditado.hotkey")

_MODIFIER_ALIASES = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "option": "alt",
    "shift": "shift",
    "cmd": "cmd",
    "command": "cmd",
    "win": "cmd",
    "super": "cmd",
    "meta": "cmd",
}


def normalize_hotkey(hotkey: str) -> str:
    """Convert ``"Ctrl+Alt+D"`` to pynput format ``"<ctrl>+<alt>+d"``."""
    parts = [p.strip().lower() for p in hotkey.replace(" ", "").split("+") if p.strip()]
    pieces: list[str] = []
    for part in parts:
        if part in _MODIFIER_ALIASES:
            pieces.append(f"<{_MODIFIER_ALIASES[part]}>")
        elif len(part) == 1:
            pieces.append(part)
        else:
            pieces.append(f"<{part}>")  # e.g. <f2>, <space>
    return "+".join(pieces)


class HotkeyListener:
    def __init__(self, hotkey: str, on_trigger: Callable[[], None]) -> None:
        self.hotkey = hotkey
        self.on_trigger = on_trigger
        self._listener = None

    def start(self) -> None:
        from pynput import keyboard

        combo = normalize_hotkey(self.hotkey)
        log.info("Registering global hotkey: %s (%s)", self.hotkey, combo)
        self._listener = keyboard.GlobalHotKeys({combo: self._safe_trigger})
        self._listener.start()

    def _safe_trigger(self) -> None:
        try:
            self.on_trigger()
        except Exception:  # noqa: BLE001
            log.exception("Error in hotkey callback")

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def join(self) -> None:
        if self._listener is not None:
            self._listener.join()
