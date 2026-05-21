# Roadmap

## Delivered (v0.2)

- **Cross-platform**: Windows, Linux, and macOS (`platform/` abstraction layer).
- **Rewritten engine** as a Python package `localditado` with tests and CI.
- **Accuracy/speed**: automatic `large-v3-turbo` + hardware-based fallback,
  `BatchedInferencePipeline`, in-memory audio, Silero VAD, `hotwords` + dictionary,
  post-processing (voice punctuation commands, capitalisation).
- **Tauri desktop app**: panel with microphone meter, settings, dictionary,
  history, diagnostics, and model download.
- **Privacy**: recordings off by default + retention policy; no telemetry.

## Next

- **Real-time streaming** (partial results while speaking) — WebSocket API is already prepared.
- Packaging: PyPI + signed installers (MSI/.deb/.AppImage/.dmg) via Releases.
- Permission onboarding (Accessibility on macOS; Wayland notice on Linux).
- Richer voice editing (delete last sentence, select text, etc.).

## Community ideas

- Hardware benchmark database (from `local-ditado doctor --json` outputs).
- Domain-specific prompt/dictionary packs: legal, medical, programming, customer support.
- More languages and ready-made profiles.
- Whisper.cpp integration for machines without Python.
- Microphone/headset setup guides.
