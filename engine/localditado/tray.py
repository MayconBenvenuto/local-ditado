"""Cross-platform system tray icon (pystray).

Runs the dictation service in-process with a global hotkey, and provides a menu to
switch profiles, toggle autostart, and open config/log. Works on Windows, macOS,
and Linux (with desktop environment tray support).
"""

from __future__ import annotations

import logging
import threading

from . import config, paths
from .platform import autostart
from .platform.hotkey import HotkeyListener
from .service import DictationService

log = logging.getLogger("localditado.tray")


def _make_icon():
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (64, 64), "#111827")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((10, 8, 54, 56), radius=12, fill="#2563eb")
    draw.rounded_rectangle((21, 14, 43, 32), radius=8, fill="#ffffff")
    draw.rectangle((27, 18, 37, 39), fill="#ffffff")
    draw.arc((18, 23, 46, 51), 0, 180, fill="#ffffff", width=4)
    draw.line((32, 49, 32, 57), fill="#ffffff", width=4)
    return image


class TrayApp:
    def __init__(self) -> None:
        self.settings = config.load_settings()
        self.service = DictationService(self.settings)
        hotkey = str(self.settings.get("hotkey", "ctrl+alt+d"))
        self.listener = HotkeyListener(hotkey, self.service.toggle)

    def set_profile(self, profile: str) -> None:
        config.update_config({"active_profile": profile})
        self.settings = config.load_settings()
        # Reload the engine in a thread so the tray is not blocked.
        threading.Thread(target=self._reload, daemon=True).start()

    def _reload(self) -> None:
        self.service = DictationService(config.load_settings())

    def _toggle_autostart(self) -> None:
        autostart.disable() if autostart.is_enabled() else autostart.enable()

    def current_profile(self) -> str:
        return str(config.load_settings().get("active_profile", "equilibrado"))

    def build_menu(self, icon):
        from pystray import Menu, MenuItem

        def profile_item(name: str, label: str):
            return MenuItem(
                label,
                lambda _i, _it: self.set_profile(name),
                checked=lambda _it, n=name: self.current_profile() == n,
                radio=True,
            )

        return Menu(
            MenuItem(lambda _i: f"Engine: {self.service.engine.model_name}", None, enabled=False),
            MenuItem(lambda _i: f"Profile: {self.current_profile()}", None, enabled=False),
            Menu.SEPARATOR,
            MenuItem("Dictate now", lambda _i, _it: self.service.toggle()),
            MenuItem(
                "Profile",
                Menu(
                    profile_item("precisao", "Precision"),
                    profile_item("equilibrado", "Balanced"),
                    profile_item("rapido", "Fast"),
                ),
            ),
            MenuItem(
                "Start on login",
                lambda _i, _it: self._toggle_autostart(),
                checked=lambda _it: autostart.is_enabled(),
            ),
            Menu.SEPARATOR,
            MenuItem("Open config", lambda _i, _it: _open(paths.config_path())),
            MenuItem("Open log", lambda _i, _it: _open(paths.log_path())),
            MenuItem("Open data folder", lambda _i, _it: _open(paths.data_dir())),
            Menu.SEPARATOR,
            MenuItem("Quit", lambda _i, _it: icon.stop()),
        )

    def run(self) -> int:
        import pystray

        self.listener.start()
        icon = pystray.Icon("Local Ditado", _make_icon(), "Local Ditado")
        icon.menu = self.build_menu(icon)
        icon.run()
        self.listener.stop()
        return 0


def _open(path) -> None:
    import os
    import subprocess
    import sys

    path = str(path)
    try:
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception:  # noqa: BLE001
        log.exception("Failed to open %s", path)


def main() -> int:
    config.ensure_config()
    return TrayApp().run()
