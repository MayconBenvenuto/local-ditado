# Local Ditado

**100% offline, private, and free voice dictation — for Windows, Linux, and macOS.**

Click any text field, press a global hotkey, speak, and the text is pasted into the
focused application. No audio sent to the cloud, no subscription. Open source.

> A free alternative to paid/freemium dictation tools: transcription runs on your
> machine with **local Whisper** (via `faster-whisper`), with GPU acceleration when available.

## Why use it

- **Total privacy** — audio never leaves your computer. No telemetry.
- **Fast and accurate** — `large-v3-turbo` model by default (with automatic fallback),
  `BatchedInferencePipeline`, and neural VAD (Silero).
- **Cross-platform** — Windows, Linux, and macOS.
- **Desktop app** — panel with microphone meter, profiles, dictionary, history, and diagnostics.
- **Extensible** — voice commands, user dictionary, profiles, and per-domain prompts.

## Installation (engine / CLI)

```bash
# Linux needs PortAudio: sudo apt install libportaudio2
pip install -e engine[app,vad]
```

For NVIDIA GPU (CUDA 12), also install:

```bash
pip install -e engine[gpu] --extra-index-url https://pypi.ngc.nvidia.com
```

## Usage (CLI)

```bash
local-ditado service     # resident service with global hotkey (main mode)
local-ditado once        # single dictation and exit
local-ditado devices     # list microphones
local-ditado test        # test microphone level
local-ditado doctor      # environment diagnostics (--json for structured output)
local-ditado tray        # system tray icon
```

Default: press **Ctrl+Alt+D**, speak, and the text is transcribed and pasted. Press again
(or go silent) to stop.

## Desktop app (Tauri)

Full graphical interface in `app/`. See [app/README.md](app/README.md) to run and package.
Panel includes: **live microphone meter**, microphone/model/hotkey/language selection,
**dictionary** of corrections, **history**, **diagnostics**, and **model download**.

## Profiles

In `profiles/`:

- `precisao` — `large-v3-turbo`, `beam_size 5`, Silero VAD, noise reduction.
- `equilibrado` — automatic model by hardware, `beam_size 5`.
- `rapido` — `base`, `beam_size 1`, lowest latency.

Switch via the app, the tray, or with `local-ditado service --profile rapido`.

## Accuracy and speed

See [docs/OPTIMIZATION.md](docs/OPTIMIZATION.md). Summary of what the project already does:

- model resolved automatically by VRAM/CPU (turbo → small → base);
- batch transcription and in-memory audio (no WAV on disk);
- neural endpointing (Silero) instead of energy threshold;
- `hotwords` + user dictionary for names and jargon;
- post-processing: voice punctuation, capitalisation, space normalisation.

## Privacy

Everything is local. Audio recordings are **off by default**; when enabled, there is
configurable retention. No network, no telemetry. See [docs/PRIVACY.md](docs/PRIVACY.md).

## Architecture

`engine/` (Python package `localditado`) is the brain; `app/` is the Tauri desktop shell
that spawns the engine as a sidecar. Details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Documentation

Full index at [docs/README.md](docs/README.md):

- [Installation](docs/INSTALL.md) · [Usage](docs/USAGE.md) · [Configuration](docs/CONFIGURATION.md)
- [Voice Commands](docs/VOICE_COMMANDS.md) · [Optimization](docs/OPTIMIZATION.md) · [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Architecture](docs/ARCHITECTURE.md) · [Sidecar API](docs/API.md) · [Privacy](docs/PRIVACY.md)

For AI agents: [AGENTS.md](AGENTS.md) (and [CLAUDE.md](CLAUDE.md)).

## Contributing

Issues and PRs are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [ROADMAP.md](ROADMAP.md).

## Credits

`faster-whisper` / CTranslate2, Silero VAD, Vosk, sounddevice, pynput, Tauri.

## License

MIT. See [LICENSE](LICENSE).
