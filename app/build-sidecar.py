#!/usr/bin/env python3
"""Bundle the Python engine as a Tauri sidecar (PyInstaller **onedir**).

Usage:
    pip install pyinstaller
    python app/build-sidecar.py

Generates the folder ``app/src-tauri/binaries/local-ditado-engine/`` containing
``local-ditado-engine(.exe)`` plus ``_internal/``. The Rust shell spawns that
executable directly (see ``main.rs``); the folder is shipped via Tauri
``resources``.

Why onedir (not ``--onefile``):
- The single-file build re-compresses ~1.5 GB every time → slow to build and
  slow to start (it self-extracts on each launch). Onedir skips both: faster
  build and near-instant startup.

Notes:
- Bundles the CUDA DLLs found in site-packages when present (see
  ``nvidia_binary_args``); otherwise it is CPU-only.
- Models are NOT embedded: they are downloaded on first use to the data directory.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import site
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT.parent / "engine"
OUT_DIR = ROOT / "src-tauri" / "binaries"
NAME = "local-ditado-engine"


def data_separator() -> str:
    return ";" if sys.platform == "win32" else ":"


def nvidia_binary_args() -> list[str]:
    """Bundle CUDA DLLs installed by NVIDIA's pip packages."""
    if sys.platform != "win32":
        return []

    args: list[str] = []
    roots = [Path(p) / "nvidia" for p in (*site.getsitepackages(), site.getusersitepackages())]
    subdirs = ("cublas/bin", "cudnn/bin", "cuda_runtime/bin", "cuda_nvrtc/bin")
    for root in roots:
        for subdir in subdirs:
            source = root / subdir
            if not source.exists():
                continue
            target = Path("nvidia") / subdir
            for dll in sorted(source.glob("*.dll")):
                args.extend(["--add-binary", f"{dll}{data_separator()}{target}"])
    return args


def _copy_bundle(bundle_dir: Path, dest_parent: Path) -> None:
    """Mirror the onedir bundle into ``dest_parent/<NAME>`` for the directly-run
    (non-installed) app and for ``tauri dev``, which resolve the sidecar next to
    the executable rather than from the installer's resource directory.

    ``dest_parent`` is ``<target>/<profile>/binaries``. We only mirror when that
    build profile has been compiled at least once (its dir exists), creating the
    ``binaries`` folder if needed.
    """
    if not dest_parent.parent.exists():
        return
    dest = dest_parent / NAME
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest_parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle_dir, dest)
    print(f"Mirrored sidecar to: {dest}")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--noconfirm",
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
        *nvidia_binary_args(),
        "--add-data", f"{ROOT.parent / 'profiles'}{data_separator()}profiles",
        "--add-data", f"{ROOT.parent / 'prompts'}{data_separator()}prompts",
        str(ENGINE / "localditado" / "_binary_entry.py"),
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(ENGINE))

    bundle_dir = OUT_DIR / NAME  # binaries/local-ditado-engine/
    if not bundle_dir.exists():
        raise SystemExit(f"PyInstaller did not produce {bundle_dir}")

    # Remove any leftover single-file binary from the old --onefile builds.
    for stale in OUT_DIR.glob(f"{NAME}-*"):
        if stale.is_file():
            stale.unlink()
            print(f"Removed stale onefile binary: {stale.name}")

    # Make the sidecar findable next to the dev and release executables.
    tauri = ROOT / "src-tauri"
    _copy_bundle(bundle_dir, tauri / "target" / "debug" / "binaries")
    _copy_bundle(bundle_dir, tauri / "target" / "release" / "binaries")
    print(f"Sidecar ready: {bundle_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
