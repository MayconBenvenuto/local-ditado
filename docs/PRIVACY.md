# Privacy

Local Ditado was built so that **none of your audio or text ever leaves your machine**.

## What happens locally

- Audio capture, transcription (Whisper/Vosk), and paste all run 100% on your computer.
- The model is downloaded **once** (from Hugging Face, on first use) and cached locally.
  After that, dictation works completely offline.

## No telemetry

- The app **does not** send any usage data, audio, or text to servers.
- The HTTP/WebSocket sidecar listens only on `127.0.0.1` (loopback) — not reachable from the network.

## Audio recordings

- **Off by default** (`save_recordings: false`).
- When enabled, WAV files are stored in the user data directory and respect
  `recordings_retention_days` (automatic cleanup; default 7 days).

## Transcription history

- Can be disabled (`save_transcript: false`).
- Stored in `history.jsonl` in the data directory; clearable via the app (History tab).

## Where files live

- Config: OS config directory (e.g. `%APPDATA%\LocalDitado` on Windows).
- Data (history, models, recordings, log): OS data directory.

Run `local-ditado doctor` to see the paths and environment — nothing leaves the machine.
