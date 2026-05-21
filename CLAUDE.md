# CLAUDE.md

Instructions for **Claude Code** in this repository. The full agent guide (layout, rules,
commands) is in `AGENTS.md` and is imported below — read it as the primary source.

@AGENTS.md

## Claude Code specifics

- **Always** run from `engine/`: `python -m ruff check localditado` and
  `python -m pytest -q` before finishing any engine change. Both must pass.
- Prefer dedicated tools (Read/Edit/Grep/Glob) over equivalent shell commands.
- The default shell is **PowerShell** (Windows). Use PowerShell syntax (`$null`, `$env:VAR`),
  or the Bash tool for POSIX scripts.
- **Current dev platform**: Windows. But the code must also run on Linux and
  macOS — respect the portability rule (OS-specifics only in `localditado/platform/`).

## Boundaries and safety

- Do not commit or push without the user asking. If asked, commit to the current branch.
- Never version local data: `config.json`, `models/`, `recordings/`, `history.jsonl`, `*.log`
  (already covered by `.gitignore`).
- Changes that send anything outside the machine contradict the project's privacy principle —
  confirm with the user first.

## Recommended task flow

1. Understand the request and locate the relevant files (most live in `engine/localditado/`).
2. Implement following the golden rules in `AGENTS.md`.
3. Run `ruff` + `pytest` from `engine/`. Add/update tests for pure logic.
4. Update corresponding documentation in `docs/` (and `docs/CONFIGURATION.md` for settings changes).
5. Summarise what changed and how to verify it.

## Quick reference for common questions

- "How do I run/verify?" → `docs/USAGE.md` and the verification section in `AGENTS.md`.
- "What are the config options?" → `docs/CONFIGURATION.md`.
- "How does the app talk to the engine?" → `docs/API.md` and `docs/ARCHITECTURE.md`.
- "Why can't I use `winreg`/`ctypes` directly?" → portability rule in `AGENTS.md`.
