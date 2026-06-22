"""Settings load and merge.

Precedence order (weakest to strongest):
``DEFAULT_SETTINGS`` < profile ``profiles/<name>.json`` < ``config.json`` < CLI overrides.

The user config lives in the OS config directory (see :mod:`localditado.paths`),
not in the repository.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import paths

DEFAULT_CONFIG_PATH = paths.config_path()
PROFILES_DIR = paths.profiles_dir()

DEFAULT_SETTINGS: dict[str, Any] = {
    "active_profile": "equilibrado",
    # Microphone
    "device": None,            # device index (None = OS default)
    "device_name": None,       # substring of the microphone name
    "sample_rate": 16000,
    # Engine
    "engine": "whisper",       # "whisper", "parakeet" (NVIDIA NeMo) or "vosk"
    "parakeet_model": "nvidia/parakeet-tdt-0.6b-v3",  # used when engine == "parakeet"
    "language": "pt",          # language code; "auto" for automatic detection
    "whisper_model": "auto",   # "auto" detects hardware; or small/medium/large-v3-turbo/...
    "whisper_device": "auto",  # "auto" | "cpu" | "cuda"
    "whisper_compute_type": "auto",  # "auto" chooses by device
    "beam_size": 5,
    "cpu_threads": 0,          # 0 = automatic (machine cores)
    "batched": True,           # BatchedInferencePipeline (faster)
    "batch_size": 8,
    "warmup": True,            # silent inference at load → fast first dictation
    # Capture / endpointing
    "vad": "silero",           # "silero" (neural) or "rms" (fallback)
    "silence_seconds": 1.5,    # silence to auto-stop
    "speech_rms_threshold": 450,
    "max_seconds": 120,        # recording safety cap
    "denoise": False,          # noise reduction before transcribing
    "denoise_method": "spectral",  # "spectral" (noisereduce) or "deepfilternet" (neural)
    # Post-processing
    "initial_prompt_file": str(paths.default_prompt_path()),
    "hotwords": "",            # terms to bias transcription (faster-whisper)
    "voice_commands": True,    # "new line", "comma", "period", ...
    "capitalize": True,
    "dictionary": {},          # literal substitutions {wrong: right}
    # Optional local-LLM "smart formatting" (offline; off by default)
    "llm_format": False,       # enable LLM cleanup of the transcript
    "llm_model_path": "",      # path to a local GGUF model (llama-cpp-python)
    "llm_gpu_layers": -1,      # -1 = offload all layers to GPU when possible
    "llm_format_instruction": "",  # override the default cleanup instruction
    # Output
    "auto_paste": True,        # paste into the focused app
    "save_transcript": True,   # append to history
    "save_recordings": False,  # privacy: WAV off by default
    "recordings_retention_days": 7,
    # Sistema
    "vosk_model": str(paths.models_dir() / "vosk-model-small-pt-0.3"),
    "hotkey": "ctrl+alt+d",
    "task_name": "LocalDitado",
    "feedback_sound": True,
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


def list_profiles() -> list[str]:
    if not PROFILES_DIR.exists():
        return []
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json"))


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

    # Resolve relative paths against the repository root.
    for key in ("initial_prompt_file", "vosk_model"):
        value = settings.get(key)
        if value:
            path = Path(str(value))
            if not path.is_absolute():
                path = paths.REPO_ROOT / path
            settings[key] = str(path)

    return settings


def ensure_config(config_path: Path | None = None) -> Path:
    """Ensure a user config.json exists, seeded with defaults."""
    config_path = config_path or DEFAULT_CONFIG_PATH
    if not config_path.exists():
        seed = {
            "active_profile": DEFAULT_SETTINGS["active_profile"],
            "device_name": None,
            "engine": "whisper",
            "language": "pt",
            "hotkey": DEFAULT_SETTINGS["hotkey"],
        }
        write_json(config_path, seed)
    return config_path


def update_config(updates: dict[str, Any], config_path: Path | None = None) -> dict[str, Any]:
    """Apply a partial patch to the user config.json and return the saved content."""
    config_path = ensure_config(config_path)
    config = read_json(config_path)
    config.update(updates)
    write_json(config_path, config)
    return config
