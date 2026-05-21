# Architecture

The project has two decoupled parts:

```
local-ditado/
├── engine/                  # Python package "localditado" — all logic
│   └── localditado/
│       ├── config.py        # settings load/merge (defaults < profile < config < CLI)
│       ├── paths.py         # OS-specific dirs (config/data/models)
│       ├── audio.py         # in-memory sounddevice capture with level meter
│       ├── vad.py           # endpointing (Silero VAD, RMS fallback)
│       ├── hardware.py      # GPU/CPU detection → choose model/device/precision
│       ├── transcribe.py    # faster-whisper + BatchedInferencePipeline + hotwords; Vosk fallback
│       ├── postprocess.py   # voice commands, dictionary, capitalisation, spacing
│       ├── service.py       # resident service: hotkey → capture → VAD → transcribe → paste
│       ├── server.py        # FastAPI + WebSocket sidecar used by the app
│       ├── tray.py          # system tray icon (pystray)
│       ├── diagnostics.py   # environment report
│       ├── cli.py           # single CLI (service/once/serve/tray/devices/test/doctor)
│       └── platform/        # all OS-specific code:
│           ├── paste.py     #   clipboard + paste (pyperclip + pynput; Cmd on macOS)
│           ├── hotkey.py    #   global hotkey (pynput)
│           ├── sound.py     #   beeps (sounddevice)
│           └── autostart.py #   login start: Registry (Win) / launchd (mac) / XDG (Linux)
└── app/                     # Tauri 2 desktop app
    ├── src/                 # frontend (HTML/CSS/JS) — Dashboard, Settings, Dictionary, History…
    └── src-tauri/           # Rust shell: window, tray, Python sidecar spawn
```

## Dictation flow

1. The global hotkey (pynput) calls `DictationService.toggle()`.
2. `audio.record_until_stop()` captures 512-sample blocks (16 kHz) **in memory**,
   emitting the level to the UI; `vad.SileroEndpointer` decides when speech has ended.
3. `transcribe.Engine` normalises the audio and transcribes (turbo + batching), with `hotwords`.
4. `postprocess` applies the dictionary, voice commands, and capitalisation.
5. `platform.paste` pastes into the focused app; `history` records the result (if enabled).

## UI ↔ engine communication

The Tauri app spawns `local-ditado serve` (sidecar). The sidecar:
- picks an ephemeral port at `127.0.0.1`, prints `{host, port, token}` to stdout, and
  writes `server.json` to the config directory;
- exposes REST (`/api/...`) and a **WebSocket `/ws`** that streams real-time events
  (microphone level, `result`, `error`).

The Rust shell reads the JSON line from stdout and delivers it to the frontend via the
`get_server` command. The WebSocket is already prepared to stream **partial results**
(future phase).

## Design decisions

- **Python remains the engine** to preserve the ecosystem (faster-whisper/CTranslate2)
  and the contributor base. Rust/Tauri is just the cross-platform shell.
- **`platform/` layer** isolates OS-specific code, so the rest of the codebase is portable.
- **Data outside the repository** (`paths.py`), following each OS's conventions.
- **Heavy dependencies are optional** (`vad`, `denoise`, `vosk`, `gpu`) via `pyproject` extras.
