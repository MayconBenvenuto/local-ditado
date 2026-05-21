# localditado (engine)

Python engine for **Local Ditado** — cross-platform offline speech-to-text dictation with
local Whisper. This package contains all the logic; the desktop interface lives in `../app`.

## Install

```bash
# Linux: sudo apt install libportaudio2 ; macOS: brew install portaudio
pip install -e ".[app,vad]"           # core + app/sidecar + neural VAD
pip install -e ".[gpu]" --extra-index-url https://pypi.ngc.nvidia.com   # NVIDIA GPU (optional)
```

## CLI

```bash
local-ditado service     # resident service with global hotkey (Ctrl+Alt+D)
local-ditado once        # single dictation and exit
local-ditado serve       # HTTP/WebSocket sidecar (used by the app)
local-ditado tray        # system tray icon
local-ditado devices     # list microphones
local-ditado test        # test microphone level
local-ditado doctor      # environment diagnostics (--json)
```

## Development

```bash
pip install -e ".[dev]"
ruff check localditado
pytest -q
```

Structure and design decisions: see `../docs/ARCHITECTURE.md`.
License: MIT.
