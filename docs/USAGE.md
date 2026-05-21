# Usage

## Basic flow

1. Start the service (`local-ditado service`) or the desktop app.
2. Click a text field in any application.
3. Press the global hotkey (**Ctrl+Alt+D** by default).
4. Speak. Stop in silence (auto-stop) or press the hotkey again.
5. The text is transcribed and **pasted** into the focused app.

## CLI

All commands: `local-ditado <subcommand>` (or `python -m localditado <subcommand>`).

| Subcommand | What it does |
| --- | --- |
| `service` | Resident service with global hotkey (main mode). |
| `once` | Does **one** dictation and exits (great for desktop shortcuts / Wayland). |
| `serve` | Starts the HTTP/WebSocket sidecar used by the app. |
| `tray` | System tray icon. |
| `devices` | Lists microphones. |
| `test` | Shows the microphone level for a few seconds. |
| `doctor` | Environment diagnostics (use `--json`). |

### Common options (`service`, `once`, `test`)

| Option | Example | Effect |
| --- | --- | --- |
| `--profile` | `--profile rapido` | Use a profile from `profiles/`. |
| `--device` | `--device 2` | Microphone index. |
| `--device-name` | `--device-name "Yeti"` | Substring of the microphone name. |
| `--model` | `--model large-v3-turbo` | Whisper model (or `auto`). |
| `--language` | `--language en` | Language (or `auto`). |
| `--engine` | `--engine vosk` | Transcription engine. |

Others: `serve --port 8000`, `test --seconds 8`, `doctor --json`.

### Examples

```bash
local-ditado devices                       # list microphones
local-ditado test --device-name "Yeti"     # test level
local-ditado service --profile equilibrado # service with a profile
local-ditado once --language en            # single dictation in English
local-ditado doctor --json > env.json      # structured diagnostics
```

## Desktop app

Screens:

- **Dashboard** — engine status, live microphone meter, "Dictate now" button,
  last transcription.
- **Settings** — microphone, model, language, hotkey, silence, VAD, denoise, voice
  commands, capitalisation, auto-paste, sound, recordings, start on login.
- **Dictionary** — automatic corrections (e.g. "maicon" → "Maycon") and hotwords.
- **History** — recent transcriptions (clearable).
- **Diagnostics** — the same report as `doctor`, on screen.
- **Models** — what was resolved for your hardware.

Closing the window does **not** quit the app: it stays in the tray. Use tray → "Quit".

## Tray

`local-ditado tray` (or the app). Allows: dictate now, switch profile, toggle start on
login, and open config/log/data folder.

## Profiles

In `profiles/` (edit the JSON or switch via the UI):

| Profile | Model | beam | silence | Focus |
| --- | --- | --- | --- | --- |
| `precisao` | `large-v3-turbo` | 5 | 2.0 s | maximum quality (denoise on) |
| `equilibrado` | `auto` (by hardware) | 5 | 1.2 s | default |
| `rapido` | `base` | 1 | 0.8 s | lowest latency |

Switch: via the UI/tray, or `local-ditado service --profile <name>`, or by editing
`active_profile` in `config.json`.

## Voice commands

Dictate punctuation and line breaks: "comma", "period", "new line"… Full list in
[VOICE_COMMANDS.md](VOICE_COMMANDS.md).
