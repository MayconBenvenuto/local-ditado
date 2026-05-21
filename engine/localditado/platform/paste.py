"""Clipboard and paste into the focused app — cross-platform.

Uses ``pyperclip`` for the clipboard and ``pynput`` to send Ctrl+V (Cmd+V on macOS).
"""

from __future__ import annotations

import logging
import sys
import time

log = logging.getLogger("localditado.paste")


def set_clipboard(text: str) -> None:
    import pyperclip

    pyperclip.copy(text)


def get_clipboard() -> str:
    import pyperclip

    return pyperclip.paste()


def _send_paste_hotkey() -> None:
    from pynput.keyboard import Controller, Key

    keyboard = Controller()
    modifier = Key.cmd if sys.platform == "darwin" else Key.ctrl
    with keyboard.pressed(modifier):
        keyboard.press("v")
        keyboard.release("v")


def paste_text(text: str, *, restore_clipboard: bool = False) -> None:
    """Paste ``text`` into the focused application via clipboard + paste hotkey."""
    text = text.strip()
    if not text:
        return

    previous = ""
    if restore_clipboard:
        try:
            previous = get_clipboard()
        except Exception:  # noqa: BLE001
            previous = ""

    set_clipboard(text)
    time.sleep(0.05)  # allow the clipboard to settle
    try:
        _send_paste_hotkey()
    except Exception:  # noqa: BLE001
        log.exception("Failed to send paste hotkey; text remains on the clipboard.")
        return

    if restore_clipboard and previous:
        time.sleep(0.2)
        try:
            set_clipboard(previous)
        except Exception:  # noqa: BLE001
            pass


def type_text(text: str) -> None:
    """Alternative: type the text character by character (without using the clipboard)."""
    from pynput.keyboard import Controller

    Controller().type(text)
