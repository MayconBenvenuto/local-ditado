import os
import subprocess
import sys
from pathlib import Path

import pystray
from PIL import Image, ImageDraw
from pystray import Menu, MenuItem

from localditado_config import DEFAULT_CONFIG_PATH, ensure_config, load_settings, read_json, write_json


ROOT = Path(__file__).resolve().parent
TASK_NAME = "LocalDitado"
LOG_PATH = ROOT / "dictado-hotkey.log"


def powershell(command: str) -> None:
    subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=ROOT,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def task_state() -> str:
    result = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            f"(Get-ScheduledTask -TaskName {TASK_NAME} -ErrorAction SilentlyContinue).State",
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    state = result.stdout.strip()
    return state or "Nao instalado"


def open_path(path: Path) -> None:
    if not path.exists():
        return
    os.startfile(path)


def set_profile(profile: str) -> None:
    ensure_config(DEFAULT_CONFIG_PATH)
    config = read_json(DEFAULT_CONFIG_PATH)
    config["active_profile"] = profile
    write_json(DEFAULT_CONFIG_PATH, config)
    restart_service()


def start_service() -> None:
    powershell(f"Start-ScheduledTask -TaskName {TASK_NAME}")


def stop_service() -> None:
    powershell(f"Stop-ScheduledTask -TaskName {TASK_NAME}")


def restart_service() -> None:
    powershell(f"Stop-ScheduledTask -TaskName {TASK_NAME} -ErrorAction SilentlyContinue; Start-ScheduledTask -TaskName {TASK_NAME}")


def install_service() -> None:
    powershell(f"& '{ROOT / 'instalar-autostart.ps1'}'")


def current_profile() -> str:
    return str(load_settings(DEFAULT_CONFIG_PATH).get("active_profile", "precisao"))


def make_icon() -> Image.Image:
    image = Image.new("RGB", (64, 64), "#111827")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((10, 8, 54, 56), radius=12, fill="#2563eb")
    draw.rectangle((27, 18, 37, 39), fill="#ffffff")
    draw.rounded_rectangle((21, 14, 43, 32), radius=8, fill="#ffffff")
    draw.arc((18, 23, 46, 51), 0, 180, fill="#ffffff", width=4)
    draw.line((32, 49, 32, 57), fill="#ffffff", width=4)
    return image


def checked_profile(profile: str):
    return lambda item: current_profile() == profile


def build_menu(icon: pystray.Icon) -> Menu:
    return Menu(
        MenuItem(lambda _: f"Status: {task_state()}", None, enabled=False),
        MenuItem(lambda _: f"Perfil atual: {current_profile()}", None, enabled=False),
        Menu.SEPARATOR,
        MenuItem("Iniciar servico", lambda _icon, _item: start_service()),
        MenuItem("Parar servico", lambda _icon, _item: stop_service()),
        MenuItem("Reiniciar servico", lambda _icon, _item: restart_service()),
        MenuItem("Instalar autostart", lambda _icon, _item: install_service()),
        Menu.SEPARATOR,
        MenuItem(
            "Perfil",
            Menu(
                MenuItem(
                    "Precisao",
                    lambda _icon, _item: set_profile("precisao"),
                    checked=checked_profile("precisao"),
                    radio=True,
                ),
                MenuItem(
                    "Equilibrado",
                    lambda _icon, _item: set_profile("equilibrado"),
                    checked=checked_profile("equilibrado"),
                    radio=True,
                ),
                MenuItem(
                    "Rapido",
                    lambda _icon, _item: set_profile("rapido"),
                    checked=checked_profile("rapido"),
                    radio=True,
                ),
            ),
        ),
        Menu.SEPARATOR,
        MenuItem("Abrir config", lambda _icon, _item: open_path(DEFAULT_CONFIG_PATH)),
        MenuItem("Abrir log", lambda _icon, _item: open_path(LOG_PATH)),
        MenuItem("Abrir pasta", lambda _icon, _item: open_path(ROOT)),
        Menu.SEPARATOR,
        MenuItem("Sair do tray", lambda _icon, _item: icon.stop()),
    )


def main() -> int:
    ensure_config(DEFAULT_CONFIG_PATH)
    icon = pystray.Icon("Local Ditado", make_icon(), "Local Ditado")
    icon.menu = build_menu(icon)
    icon.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
