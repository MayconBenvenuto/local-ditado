"""Environment report: OS, hardware, packages, and microphones.

Reused by the CLI (``local-ditado doctor``) and the app's Diagnostics screen.
Everything is local; nothing leaves the machine.
"""

from __future__ import annotations

import importlib.metadata
import platform
import sys
from dataclasses import asdict

from . import audio, config, hardware


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not installed"


def build_report(config_path=None) -> dict:
    settings = config.load_settings(config_path)
    hw = hardware.detect()
    try:
        devices = [asdict(d) for d in audio.list_input_devices()]
    except Exception as exc:  # noqa: BLE001
        devices = [{"error": str(exc)}]

    try:
        model, device, compute_type = hardware.resolve(settings)
        resolved = {"model": model, "device": device, "compute_type": compute_type}
    except Exception as exc:  # noqa: BLE001
        resolved = {"error": str(exc)}

    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "hardware": asdict(hw),
        "resolved_engine": resolved,
        "packages": {
            name: package_version(name)
            for name in (
                "faster-whisper",
                "ctranslate2",
                "sounddevice",
                "pynput",
                "pyperclip",
                "silero-vad",
                "onnxruntime",
                "vosk",
                "noisereduce",
                "deepfilternet",
                "nemo_toolkit",
                "llama-cpp-python",
            )
        },
        "input_devices": devices,
        "active_profile": settings.get("active_profile"),
    }


def print_report(report: dict) -> None:
    print("== Local Ditado — diagnostics ==")
    print(f"Python:   {report['python']}")
    print(f"OS:       {report['platform']}")
    hw = report["hardware"]
    print(f"GPU CUDA: {'yes' if hw['has_cuda'] else 'no'} "
          f"(gpus={hw['cuda_devices']}, vram={hw['vram_mb']}MB, cpus={hw['cpu_count']})")
    print(f"Engine:   {report['resolved_engine']}")
    print(f"Profile:  {report['active_profile']}")
    print("\nPackages:")
    for name, version in report["packages"].items():
        print(f"  - {name}: {version}")
    print("\nMicrophones:")
    for dev in report["input_devices"]:
        if "error" in dev:
            print(f"  ! {dev['error']}")
        else:
            print(f"  {dev['index']}: {dev['name']} "
                  f"(channels={dev['channels']}, {dev['default_sample_rate']} Hz)")
