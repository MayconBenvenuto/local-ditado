"""Iniciar no login — multiplataforma.

- Windows: chave de registro ``HKCU\\...\\Run``.
- macOS: ``~/Library/LaunchAgents/com.localditado.service.plist`` (launchd).
- Linux: ``~/.config/autostart/local-ditado.desktop`` (XDG autostart).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

log = logging.getLogger("localditado.autostart")

_APP_ID = "com.localditado.service"
_RUN_NAME = "LocalDitado"


def default_command() -> list[str]:
    """Command that starts the resident service (headless mode)."""
    if getattr(sys, "frozen", False):  # PyInstaller binary
        return [sys.executable, "service"]
    return [sys.executable, "-m", "localditado.cli", "service"]


def _quote(cmd: list[str]) -> str:
    return " ".join(f'"{c}"' if " " in c else c for c in cmd)


# --------------------------- Windows ---------------------------
def _win_key():
    import winreg

    return winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_ALL_ACCESS,
    )


def _win_enable(cmd: list[str]) -> None:
    import winreg

    with _win_key() as key:
        winreg.SetValueEx(key, _RUN_NAME, 0, winreg.REG_SZ, _quote(cmd))


def _win_disable() -> None:
    import winreg

    try:
        with _win_key() as key:
            winreg.DeleteValue(key, _RUN_NAME)
    except FileNotFoundError:
        pass


def _win_is_enabled() -> bool:
    import winreg

    try:
        with _win_key() as key:
            winreg.QueryValueEx(key, _RUN_NAME)
        return True
    except FileNotFoundError:
        return False


# --------------------------- macOS ---------------------------
def _mac_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{_APP_ID}.plist"


def _mac_enable(cmd: list[str]) -> None:
    args = "".join(f"    <string>{c}</string>\n" for c in cmd)
    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        f"  <key>Label</key><string>{_APP_ID}</string>\n"
        "  <key>ProgramArguments</key><array>\n"
        f"{args}"
        "  </array>\n"
        "  <key>RunAtLoad</key><true/>\n"
        "</dict></plist>\n"
    )
    path = _mac_plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plist, encoding="utf-8")


def _mac_disable() -> None:
    _mac_plist_path().unlink(missing_ok=True)


def _mac_is_enabled() -> bool:
    return _mac_plist_path().exists()


# --------------------------- Linux ---------------------------
def _linux_desktop_path() -> Path:
    import os

    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "autostart" / "local-ditado.desktop"


def _linux_enable(cmd: list[str]) -> None:
    desktop = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Local Ditado\n"
        f"Exec={_quote(cmd)}\n"
        "X-GNOME-Autostart-enabled=true\n"
        "Terminal=false\n"
    )
    path = _linux_desktop_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(desktop, encoding="utf-8")


def _linux_disable() -> None:
    _linux_desktop_path().unlink(missing_ok=True)


def _linux_is_enabled() -> bool:
    return _linux_desktop_path().exists()


# --------------------------- Public API ---------------------------
def enable(command: list[str] | None = None) -> None:
    cmd = command or default_command()
    if sys.platform == "win32":
        _win_enable(cmd)
    elif sys.platform == "darwin":
        _mac_enable(cmd)
    else:
        _linux_enable(cmd)
    log.info("Autostart habilitado: %s", _quote(cmd))


def disable() -> None:
    if sys.platform == "win32":
        _win_disable()
    elif sys.platform == "darwin":
        _mac_disable()
    else:
        _linux_disable()
    log.info("Autostart desabilitado")


def is_enabled() -> bool:
    if sys.platform == "win32":
        return _win_is_enabled()
    if sys.platform == "darwin":
        return _mac_is_enabled()
    return _linux_is_enabled()
