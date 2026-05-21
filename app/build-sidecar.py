#!/usr/bin/env python3
"""Bundle the Python engine as a single binary (Tauri sidecar).

Usage:
    pip install pyinstaller
    python app/build-sidecar.py

Generates ``app/src-tauri/binaries/local-ditado-engine-<target-triple>(.exe)``, which is
the name Tauri expects for ``externalBin``.

Notes:
- Bundles CPU-only by default. For GPU/CUDA, install the [gpu] extras first and
  adjust the --collect-all flags as needed (the bundle will be large).
- Models are NOT embedded: they are downloaded on first use to the data directory.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT.parent / "engine"
OUT_DIR = ROOT / "src-tauri" / "binaries"
NAME = "local-ditado-engine"


def target_triple() -> str:
    try:
        out = subprocess.run(["rustc", "-vV"], capture_output=True, text=True, check=True).stdout
        for line in out.splitlines():
            if line.startswith("host:"):
                return line.split("host:")[1].strip()
    except Exception:
        pass
    # Reasonable fallback per OS.
    return {
        "win32": "x86_64-pc-windows-msvc",
        "darwin": "aarch64-apple-darwin",
    }.get(sys.platform, "x86_64-unknown-linux-gnu")


def main() -> int:
    triple = target_triple()
    ext = ".exe" if sys.platform == "win32" else ""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", NAME,
        "--distpath", str(OUT_DIR),
        "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "build"),
        "--collect-all", "faster_whisper",
        "--collect-all", "ctranslate2",
        "--collect-all", "sounddevice",
        "--collect-submodules", "uvicorn",
        "--hidden-import", "fastapi",
        "--hidden-import", "pynput",
        "--hidden-import", "pyperclip",
        str(ENGINE / "localditado" / "__main__.py"),
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(ENGINE))

    produced = OUT_DIR / f"{NAME}{ext}"
    final = OUT_DIR / f"{NAME}-{triple}{ext}"
    if produced.exists():
        shutil.move(str(produced), str(final))
    print(f"Sidecar ready: {final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
