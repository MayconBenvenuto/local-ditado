# Troubleshooting and FAQ

Always start with:

```bash
local-ditado doctor
```

It shows Python, OS, GPU/CPU, resolved model, packages, and microphones — all local.
The log is at `local-ditado.log` (in the data directory; path shown by `doctor`).

## Installation

**`OSError: PortAudio library not found` / `sounddevice` fails**
The system library is missing. Linux: `sudo apt install libportaudio2`. macOS: `brew install portaudio`.

**`pip install` fails while compiling something**
Update pip (`python -m pip install --upgrade pip`) and use Python 3.10+.

## Microphone

**"Microphone not found by name"**
Run `local-ditado devices` and use an exact substring of the name in `device_name`, or use the index in `device`.

**Records but output text is empty**
Test the level: `local-ditado test --device-name "<your mic>"`. If the level stays near 0,
the wrong microphone is selected or the gain is too low. Speak closer or increase the volume.

**Stops too early (or never stops)**
Increase `silence_seconds` (higher = waits longer). In noisy environments, prefer `vad: "silero"`.
In `rms` mode, adjust `speech_rms_threshold`.

## GPU / performance

**`doctor` shows `GPU CUDA: no` even with an NVIDIA card**
Install the GPU extra: `pip install -e engine[gpu] --extra-index-url https://pypi.ngc.nvidia.com`
and verify drivers/CUDA 12 (`nvidia-smi`). On Windows, the engine loads CUDA DLLs from pip automatically.

**Transcription is slow**
Confirm `device: cuda` in `doctor`. On CPU, use a smaller model (`small`/`base`), keep
`batched: true`, reduce `beam_size` to 1 (the `rapido` profile).

**Out of GPU memory**
`auto` should fall back to a smaller model; if you pinned `large-v3-turbo`, switch to `small`
or use `whisper_compute_type: "int8_float16"`.

## Global hotkey and paste

**The hotkey does not trigger**

- macOS: grant **Accessibility** permission to the terminal/app (System Settings → Privacy &
  Security → Accessibility).
- Linux/Wayland: global hotkeys are limited. Use an X11 session, or register `local-ditado once`
  as a keyboard shortcut in your desktop environment.
- Check for conflicts with another app using the same combination; change `hotkey` in config.

**Transcribes but does not paste**
The text is on the clipboard (just paste with Ctrl/Cmd+V). On macOS this also requires the
Accessibility permission. On Linux, install `xclip`/`wl-clipboard`.

## Desktop app (Tauri)

**"sidecar not found" in the interface**
The engine binary was not bundled. Run `python app/build-sidecar.py` (generates
`app/src-tauri/binaries/local-ditado-engine-<target>`), or use dev mode with `?api=`.

**`npm run build` complains about icons**
Generate icons once: `npm run tauri icon src-tauri/icons/icon.png`.

## Privacy / data

**Where are my files?**
See the paths in `doctor`. Config in the OS config directory; history, models, and
recordings in the OS data directory.

**How do I delete everything?**
Clear the history via the UI (History tab), delete the data folder, and uninstall with
`pip uninstall local-ditado`. Recordings are off by default.

## Still stuck?

Open an issue including the output of `local-ditado doctor --json` (without sensitive data),
the model used, and the steps to reproduce. See [../CONTRIBUTING.md](../CONTRIBUTING.md).
