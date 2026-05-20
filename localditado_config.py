import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT / "config.json"
EXAMPLE_CONFIG_PATH = ROOT / "config.example.json"
DEFAULT_PROMPT_PATH = ROOT / "prompts" / "pt-br-default.txt"
DEFAULT_VOSK_MODEL_PATH = ROOT / "models" / "vosk-model-small-pt-0.3"
PROFILES_DIR = ROOT / "profiles"


DEFAULT_SETTINGS: dict[str, Any] = {
    "active_profile": "precisao",
    "device": None,
    "device_name": None,
    "engine": "whisper",
    "whisper_model": "small",
    "whisper_device": "cuda",
    "whisper_compute_type": "int8_float16",
    "silence_seconds": 2.5,
    "beam_size": 5,
    "cpu_threads": 8,
    "sample_rate": 16000,
    "speech_rms_threshold": 450,
    "initial_prompt_file": str(DEFAULT_PROMPT_PATH),
    "vosk_model": str(DEFAULT_VOSK_MODEL_PATH),
    "task_name": "LocalDitado",
    "hotkey": "Ctrl+Alt+D",
}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def profile_path(profile_name: str) -> Path:
    return PROFILES_DIR / f"{profile_name}.json"


def load_settings(
    config_path: Path | None = None,
    profile_name: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config_path = config_path or DEFAULT_CONFIG_PATH
    settings = dict(DEFAULT_SETTINGS)
    config = read_json(config_path)

    selected_profile = profile_name or config.get("active_profile") or settings["active_profile"]
    profile = read_json(profile_path(str(selected_profile)))

    settings.update(profile)
    settings.update(config)
    settings["active_profile"] = selected_profile

    if overrides:
        settings.update({key: value for key, value in overrides.items() if value is not None})

    for key in ("initial_prompt_file", "vosk_model"):
        if settings.get(key):
            path = Path(str(settings[key]))
            if not path.is_absolute():
                path = ROOT / path
            settings[key] = str(path)

    return settings


def ensure_config(config_path: Path | None = None) -> Path:
    config_path = config_path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        if EXAMPLE_CONFIG_PATH.exists():
            config_path.write_text(EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            write_json(config_path, DEFAULT_SETTINGS)
    return config_path
