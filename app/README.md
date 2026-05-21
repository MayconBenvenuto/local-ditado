# Local Ditado — desktop app (Tauri)

Cross-platform desktop interface (Windows, Linux, macOS) built with **Tauri 2**.
Rust provides the shell (window + tray) and spawns the **Python sidecar** (`local-ditado-engine`),
which contains all dictation logic. The UI (HTML/CSS/JS in `src/`) communicates with the
sidecar over HTTP + WebSocket at `127.0.0.1`.

## Prerequisites

- Node.js 18+ and Rust (stable toolchain) — see [tauri.app/start/prerequisites](https://tauri.app/start/prerequisites)
- Python 3.10+ with the engine package installed:
  ```bash
  pip install -e ../engine[app]
  ```

## Generate icons (once)

`tauri.conf.json` references icons in `src-tauri/icons/`. Generate them from the source PNG:

```bash
npm install
npm run tauri icon src-tauri/icons/icon.png
```

## Bundle the Python sidecar

The app expects the engine binary at `src-tauri/binaries/local-ditado-engine-<target-triple>`:

```bash
pip install pyinstaller
python build-sidecar.py
```

## Development

Two options:

**A) All-in-one (Tauri spawns the sidecar):**
```bash
npm install
npm run dev
```

**B) UI in the browser, manual sidecar (faster frontend iteration):**
```bash
# terminal 1
python -m localditado.cli serve            # prints {"host","port","token"}
# terminal 2: serve src/ and open with ?api=http://127.0.0.1:<port>
```

## Production build

```bash
python build-sidecar.py          # generate the engine binary
npm run tauri icon src-tauri/icons/icon.png
npm run build                     # output installers in src-tauri/target/release/bundle/
```

Outputs: `.msi`/`.exe` (Windows), `.deb`/`.AppImage`/`.rpm` (Linux), `.dmg` (macOS).
