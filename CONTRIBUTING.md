# Contributing

Thank you for considering a contribution to Local Ditado! The project is open source and
wants to grow with the community.

## How to help

- Test on different microphones, GPUs, and operating systems (Windows, Linux, macOS).
- Report bugs with the output of `local-ditado doctor --json`, the model used, and your config.
- Improve accuracy: profiles, prompts, and domain-specific dictionaries.
- Work on upcoming features (see [ROADMAP.md](ROADMAP.md)) — real-time streaming is the top priority.
- Improve the desktop app (`app/`) and documentation.

## Structure

- `engine/` — Python package `localditado` (all the logic). See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- `app/` — Tauri desktop app (Rust shell + frontend) that spawns the engine as a sidecar.

## Development (engine)

```bash
# Linux: sudo apt install libportaudio2
cd engine
pip install -e ".[dev,app,vad]"
ruff check localditado      # lint
mypy localditado            # types (informational)
pytest -q                   # tests
```

## Development (app)

See [app/README.md](app/README.md).

## Before opening a pull request

- Run `ruff check` and `pytest` from `engine/`.
- Do not include local data (`models/`, `recordings/`, logs, `config.json`, transcripts).
- Explain the problem the change solves.
- Changed performance? Include comparative timings. Changed accuracy? Include examples or a test recording.
- Keep the code portable: nothing OS-specific outside `engine/localditado/platform/`.
