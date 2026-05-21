"""Hardware detection and automatic model / device / precision selection.

The goal is to deliver the best accuracy×speed combination the machine can handle,
falling back from ``large-v3-turbo`` to smaller models when VRAM/CPU is insufficient.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass

log = logging.getLogger("localditado.hardware")

# Default model when there is ample GPU. "large" accuracy at roughly "base" speed.
TURBO_MODEL = "large-v3-turbo"


@dataclass
class Hardware:
    has_cuda: bool
    cuda_devices: int
    vram_mb: int
    cpu_count: int


def _cuda_device_count() -> int:
    try:
        import ctranslate2

        return int(ctranslate2.get_cuda_device_count())
    except Exception:  # noqa: BLE001
        return 0


def _query_vram_mb() -> int:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return max(int(line) for line in out.stdout.strip().splitlines())
    except Exception:  # noqa: BLE001
        pass
    return 0


def detect() -> Hardware:
    cuda_devices = _cuda_device_count()
    has_cuda = cuda_devices > 0
    vram_mb = _query_vram_mb() if has_cuda else 0
    cpu_count = os.cpu_count() or 4
    hw = Hardware(
        has_cuda=has_cuda, cuda_devices=cuda_devices, vram_mb=vram_mb, cpu_count=cpu_count
    )
    log.info(
        "Hardware: cuda=%s gpus=%s vram=%sMB cpus=%s",
        hw.has_cuda,
        hw.cuda_devices,
        hw.vram_mb,
        hw.cpu_count,
    )
    return hw


def choose_device(requested: str, hw: Hardware) -> str:
    if requested and requested != "auto":
        return requested
    return "cuda" if hw.has_cuda else "cpu"


def choose_compute_type(requested: str, device: str) -> str:
    if requested and requested != "auto":
        return requested
    # int8_float16 saves VRAM while keeping quality; int8 is best for CPU.
    return "int8_float16" if device == "cuda" else "int8"


def choose_model(requested: str, hw: Hardware) -> str:
    """Resolve ``whisper_model`` when set to ``auto``."""
    if requested and requested != "auto":
        return requested

    if hw.has_cuda:
        if hw.vram_mb >= 6000 or hw.vram_mb == 0:  # 0 = nvidia-smi failed but CUDA is present
            return TURBO_MODEL
        if hw.vram_mb >= 2500:
            return "small"
        return "base"

    # CPU: turbo is heavy; "small" is the best default balance.
    if hw.cpu_count >= 8:
        return "small"
    return "base"


def resolve(settings: dict) -> tuple[str, str, str]:
    """Return (model, device, compute_type) resolved from settings."""
    hw = detect()
    device = choose_device(str(settings.get("whisper_device", "auto")), hw)
    compute_type = choose_compute_type(str(settings.get("whisper_compute_type", "auto")), device)
    model = choose_model(str(settings.get("whisper_model", "auto")), hw)
    log.info("Resolved: model=%s device=%s compute_type=%s", model, device, compute_type)
    return model, device, compute_type
