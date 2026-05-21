# AGENTS.md — guide for AI coding agents

This file orients coding agents (Claude Code, Cursor, Copilot, etc.) working in this
repository. Humans can also read it as a quick map of the project.

> Convention: this file follows the [agents.md](https://agents.md) standard. `CLAUDE.md`
> imports this content, so **keep agent instructions here** (single source of truth).

## What the project is

**Local Ditado** — offline **speech-to-text** dictation with local Whisper, a global
hotkey, and auto-paste into the focused app. Cross-platform (Windows, Linux, macOS),
open source (MIT), no telemetry. Goal: a free alternative to paid/freemium dictation tools.

> Watch out for a common misconception: this is **STT (speech → text)**, not TTS.

## Repository layout

```
engine/                 # Python package "localditado" — ALL logic lives here
  localditado/
    config.py           # settings (defaults < profile < config.json < CLI)
    paths.py            # OS-specific dirs (config/data/models)
    audio.py            # in-memory sounddevice capture + level meter
    vad.py              # endpointing: Silero VAD (fallback RMS)
    hardware.py         # detect GPU/CPU → choose model/device/precision
    transcribe.py       # faster-whisper + batching + hotwords; Vosk fallback
    postprocess.py      # voice commands, dictionary, capitalisation
    service.py          # resident service (hotkey→capture→VAD→transcribe→paste)
    server.py           # sidecar FastAPI+WebSocket (used by the app)
    tray.py             # system tray icon (pystray)
    diagnostics.py      # environment report
    cli.py              # CLI (service/once/serve/tray/devices/test/doctor)
    platform/           # **all OS-specific code lives here** (paste/hotkey/sound/autostart)
  tests/                # pytest
  pyproject.toml        # packaging, deps, extras, ruff, mypy
app/                    # Tauri 2 desktop app
  src/                  # frontend (HTML/CSS/JS): Dashboard, Settings, Dictionary, History…
  src-tauri/            # Rust shell: window, tray, sidecar spawn
  build-sidecar.py      # PyInstaller → engine binary for Tauri
profiles/               # precisao/equilibrado/rapido profiles (JSON)
prompts/                # context prompt
docs/                   # documentation (see docs/README.md)
*.py (root)             # backward-compat shims that delegate to the new CLI
```

## Setup

```bash
# Linux: sudo apt install libportaudio2 ; macOS: brew install portaudio
cd engine
pip install -e ".[dev,app,vad]"
```

## Essential commands (run from `engine/`)

| Action | Command |
| --- | --- |
| Lint | `python -m ruff check localditado` |
| Types | `python -m mypy localditado` (informational) |
| Tests | `python -m pytest -q` |
| Run CLI | `python -m localditado <subcommand>` |
| Diagnostics | `python -m localditado doctor` |

Before finishing any engine change: **ruff + pytest must pass**.

## Golden rules (don't break)

1. **Portability**: nothing OS-specific outside `engine/localditado/platform/`.
   No `import winreg`, `ctypes.windll`, `winsound`, `os.startfile`, or `C:\...` paths
   in shared code. Use the `platform/` layer.
2. **User data outside the repo**: always use `localditado.paths` (never write next to
   the code). Config/history/models/recordings go to OS data directories.
3. **Privacy**: no network traffic beyond the sidecar loopback. No telemetry. Audio
   recordings remain **off by default**.
4. **Heavy dependencies are optional** and **lazily imported** (inside functions):
   `faster_whisper`, `torch`/`silero_vad`, `pynput`, `pyperclip`, `sounddevice`, `fastapi`,
   `pystray`, `vosk`, `noisereduce`. Importing the package must not require all of them.
5. **Style**: `ruff` (line length 100, rules E/F/I/UP/B/W). Type hints on new code.
6. **Language**: docstrings, comments, and UI text in **English**.

## How to add things

- **New config key**: add it to `DEFAULT_SETTINGS` in `config.py`, read it via
  `settings.get(...)`, document it in `docs/CONFIGURATION.md`, and expose it in
  `app/src` if useful.
- **New voice command**: edit `VOICE_COMMANDS` in `postprocess.py` (longer phrases first),
  cover it with a test in `tests/test_postprocess.py`, and list it in `docs/VOICE_COMMANDS.md`.
- **New CLI subcommand**: add a `cmd_*` function + subparser in `cli.py`.
- **New sidecar endpoint**: add it in `server.py` and document it in `docs/API.md`.
- **OS-specific behaviour**: implement in `platform/<module>.py` with a `sys.platform`
  dispatch and a safe fallback.

## Architecture in one sentence

The **Python engine** (`engine/`) is the brain; the **Tauri app** (`app/`) is just the
desktop shell that spawns the engine as a **sidecar** (`local-ditado serve`) and talks
to it over HTTP + WebSocket at `127.0.0.1`. Details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Known pitfalls

- **No mic/GPU in CI**: tests must not depend on real audio or a loaded model.
  Test pure logic (config, postprocess, hardware, hotkey).
- **Wayland (Linux)**: global hotkey is limited under pynput — document and offer `once` via desktop shortcut.
- **macOS**: paste/hotkey require Accessibility permission.
- **Large model**: `large-v3-turbo` needs VRAM/RAM; the `hardware.py` fallback is essential — do not remove it.

## Quick manual check (no hardware needed)

```bash
cd engine
python -m ruff check localditado && python -m pytest -q
python -m localditado --help
python -m localditado doctor      # prints environment info; sends nothing
```
