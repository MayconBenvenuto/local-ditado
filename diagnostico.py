import argparse
import importlib.metadata
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import pyaudio

from localditado_config import DEFAULT_CONFIG_PATH, load_settings


ROOT = Path(__file__).resolve().parent


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "nao instalado"


def run_command(command: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        return result.returncode, (result.stdout or result.stderr).strip()
    except Exception as exc:
        return 1, str(exc)


def list_devices() -> list[dict[str, object]]:
    pa = pyaudio.PyAudio()
    try:
        devices = []
        for index in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(index)
            channels = int(info.get("maxInputChannels", 0))
            if channels <= 0:
                continue
            devices.append(
                {
                    "index": index,
                    "name": info.get("name"),
                    "channels": channels,
                    "default_sample_rate": int(info.get("defaultSampleRate", 0)),
                }
            )
        return devices
    finally:
        pa.terminate()


def print_devices() -> None:
    for device in list_devices():
        print(
            f"{device['index']}: {device['name']} | "
            f"canais={device['channels']} | padrao={device['default_sample_rate']} Hz"
        )


def whisper_probe(settings: dict[str, object]) -> dict[str, object]:
    started = time.perf_counter()
    try:
        import dictado_hotkey

        if dictado_hotkey.WhisperModel is None:
            return {"ok": False, "error": "faster-whisper nao instalado"}

        dictado_hotkey.WhisperModel(
            str(settings["whisper_model"]),
            device=str(settings["whisper_device"]),
            compute_type=str(settings["whisper_compute_type"]),
            cpu_threads=int(settings["cpu_threads"]),
        )
        return {"ok": True, "load_seconds": round(time.perf_counter() - started, 2)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def build_report(config_path: Path) -> dict[str, object]:
    settings = load_settings(config_path)
    nvidia_code, nvidia_output = run_command(["nvidia-smi"])
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "config_path": str(config_path),
        "settings": settings,
        "packages": {
            "faster-whisper": package_version("faster-whisper"),
            "ctranslate2": package_version("ctranslate2"),
            "PyAudio": package_version("PyAudio"),
            "vosk": package_version("vosk"),
            "nvidia-cublas-cu12": package_version("nvidia-cublas-cu12"),
            "nvidia-cudnn-cu12": package_version("nvidia-cudnn-cu12"),
            "nvidia-cuda-runtime-cu12": package_version("nvidia-cuda-runtime-cu12"),
        },
        "nvidia_smi": {
            "ok": nvidia_code == 0,
            "output": nvidia_output.splitlines()[:8],
        },
        "input_devices": list_devices(),
        "whisper_probe": whisper_probe(settings),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnostico do Local Ditado.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--json", action="store_true", help="Imprime o diagnostico em JSON.")
    parser.add_argument("--devices-only", action="store_true", help="Lista apenas microfones.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.devices_only:
        print_devices()
        return 0

    report = build_report(args.config)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print("== Local Ditado diagnostico ==")
    print(f"Python: {report['python'].split()[0]}")
    print(f"Windows: {report['platform']}")
    print(f"Config: {report['config_path']}")
    print("\nPacotes:")
    for name, version in report["packages"].items():
        print(f"- {name}: {version}")
    print("\nGPU:")
    print("OK" if report["nvidia_smi"]["ok"] else "Nao detectada pelo nvidia-smi")
    for line in report["nvidia_smi"]["output"]:
        print(line)
    print("\nMicrofones:")
    print_devices()
    print("\nWhisper:")
    print(report["whisper_probe"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
