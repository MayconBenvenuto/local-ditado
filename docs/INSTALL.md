# Installation

Local Ditado has two parts: the **engine** (CLI/Python service) and, optionally, the
**desktop app** (Tauri). For most users, installing the engine is enough.

## Requirements

- **Python 3.10+**
- **PortAudio** (for audio capture):
  - Windows: bundled with `sounddevice` — nothing extra needed.
  - Linux: `sudo apt install libportaudio2` (or your distro's `portaudio` package).
  - macOS: `brew install portaudio`.
- **NVIDIA GPU (optional)**: drivers + CUDA 12 for hardware acceleration.

## Quick install

### Linux / macOS

```bash
bash install.sh
```

The installer checks Python, installs the engine, lists microphones, and runs diagnostics.

## Manual install (any OS)

```bash
# Linux: sudo apt install libportaudio2
# macOS: brew install portaudio
pip install -e engine[app,vad]
```

Available extras (combine as needed, e.g. `engine[app,vad,vosk]`):

| Extra | Purpose |
| --- | --- |
| `app` | desktop app sidecar + tray (FastAPI, uvicorn, pystray, Pillow) |
| `vad` | Silero neural endpointing (onnxruntime, silero-vad) — recommended |
| `denoise` | noise reduction (noisereduce, scipy) |
| `vosk` | offline fallback with Vosk |
| `gpu` | CUDA 12 libraries (install with the NVIDIA index, see below) |
| `dev` | ruff, mypy, pytest |

## NVIDIA GPU (CUDA 12)

```bash
pip install -e engine[gpu] --extra-index-url https://pypi.ngc.nvidia.com
```

On Windows, the engine automatically exposes the CUDA DLLs installed via pip
(cuBLAS/cuDNN/runtime). Verify with:

```bash
local-ditado doctor
```

Look for `GPU CUDA: yes` and, under `Engine`, `device: cuda`.

## Desktop app (Tauri)

See [../app/README.md](../app/README.md). Summary:

```bash
cd app
npm install
npm run tauri icon src-tauri/icons/icon.png   # generate icons (once)
python build-sidecar.py                        # bundle the engine (PyInstaller)
npm run dev                                     # or: npm run build
```

Tauri prerequisites (Rust + system libs): [tauri.app/start/prerequisites](https://tauri.app/start/prerequisites)

## Start on login

- Via the UI: desktop app (Settings → "Start on login") or tray ("Start on login").
- Under the hood: Windows Registry, `launchd` on macOS, `~/.config/autostart` on Linux
  (see `localditado/platform/autostart.py`).

## Uninstall

```bash
pip uninstall local-ditado
```

Also remove user data if desired (paths shown by `local-ditado doctor`).

## Problems?

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
