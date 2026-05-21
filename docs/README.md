# Local Ditado — Documentation

Offline, private, and free speech-to-text dictation for Windows, Linux, and macOS.

## For users

- [Installation](INSTALL.md) — per OS, GPU options, and dependencies.
- [Usage](USAGE.md) — CLI, desktop app, tray, and profiles.
- [Configuration](CONFIGURATION.md) — all options and what each one does.
- [Voice Commands](VOICE_COMMANDS.md) — dictate punctuation and line breaks.
- [Optimization](OPTIMIZATION.md) — how to gain accuracy and speed.
- [Troubleshooting](TROUBLESHOOTING.md) — common errors and FAQ.
- [Privacy](PRIVACY.md) — what stays local and what (never) leaves the machine.

## For developers / integrators

- [Architecture](ARCHITECTURE.md) — how the engine and the app fit together.
- [Sidecar API](API.md) — REST + WebSocket used by the interface.
- [Contributing](../CONTRIBUTING.md) — dev setup, tests, and PRs.
- [Agent guide (AI)](../AGENTS.md) — rules for coding agents.
- [Community](COMMUNITY.md) — positioning and channels.
- [Roadmap](../ROADMAP.md) — what comes next.

## 30-second overview

1. Install (`pip install -e engine[app,vad]`).
2. Run `local-ditado service`.
3. Click a text field, press **Ctrl+Alt+D**, speak, and the text is pasted.

Everything runs on your machine: audio never leaves the computer.
