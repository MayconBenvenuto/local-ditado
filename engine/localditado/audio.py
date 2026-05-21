"""Cross-platform audio capture via sounddevice.

Replaces PyAudio (harder to install on Linux/macOS) and returns audio
directly as ``numpy.float32`` in memory — no intermediate WAV on disk.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import numpy as np

try:
    import sounddevice as sd
except OSError as exc:  # PortAudio missing on the OS
    sd = None  # type: ignore[assignment]
    _SD_IMPORT_ERROR: Exception | None = exc
except ImportError as exc:
    sd = None  # type: ignore[assignment]
    _SD_IMPORT_ERROR = exc
else:
    _SD_IMPORT_ERROR = None

log = logging.getLogger("localditado.audio")

FRAME_SAMPLES = 512  # block size required by Silero VAD at 16 kHz


def _require_sd() -> None:
    if sd is None:
        raise RuntimeError(
            "sounddevice/PortAudio unavailable. Install the system library "
            "(Linux: 'sudo apt install libportaudio2'; macOS: 'brew install portaudio'). "
            f"Detail: {_SD_IMPORT_ERROR}"
        )


@dataclass
class InputDevice:
    index: int
    name: str
    channels: int
    default_sample_rate: int


class Endpointer(Protocol):
    """Detects end of speech. Implemented by RMS or Silero (see :mod:`localditado.vad`)."""

    def reset(self) -> None: ...

    def is_speech(self, frame: np.ndarray) -> bool: ...


def list_input_devices() -> list[InputDevice]:
    _require_sd()
    devices: list[InputDevice] = []
    for index, info in enumerate(sd.query_devices()):
        channels = int(info.get("max_input_channels", 0))
        if channels <= 0:
            continue
        devices.append(
            InputDevice(
                index=index,
                name=str(info.get("name", f"device {index}")),
                channels=channels,
                default_sample_rate=int(info.get("default_samplerate", 0)),
            )
        )
    return devices


def find_device_index(device_name: str | None, sample_rate: int) -> int | None:
    if not device_name:
        return None
    needle = device_name.lower()
    matches: list[tuple[int, int, str]] = []
    for dev in list_input_devices():
        if needle not in dev.name.lower():
            continue
        rate = dev.default_sample_rate
        score = 0 if rate == sample_rate else abs(rate - sample_rate)
        matches.append((score, dev.index, dev.name))
    if not matches:
        raise RuntimeError(f"Microphone not found by name: {device_name}")
    matches.sort()
    _, index, name = matches[0]
    log.info("Microphone selected by name: %s (%s)", index, name)
    return index


def resolve_device_index(
    device: int | None, device_name: str | None, sample_rate: int
) -> int | None:
    if device is not None:
        return device
    return find_device_index(device_name, sample_rate)


def rms_level(samples: np.ndarray) -> float:
    """Normalised RMS level in [0, 1] for a float32 block."""
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))


def record_until_stop(
    stop_event: threading.Event,
    *,
    device: int | None,
    sample_rate: int = 16000,
    silence_seconds: float = 1.5,
    max_seconds: float = 120.0,
    endpointer: Endpointer | None = None,
    speech_rms_threshold: float = 450.0,
    on_level: Callable[[float], None] | None = None,
) -> np.ndarray:
    """Record from the microphone until silence, ``stop_event``, or ``max_seconds``.

    Returns mono audio as ``float32`` in the range [-1, 1]. ``on_level`` receives the
    RMS level of each block (0..1) to feed a live meter in the interface.
    """
    _require_sd()
    if endpointer is not None:
        endpointer.reset()

    # speech_rms_threshold comes from the int16 world (legacy); convert to float scale.
    float_threshold = speech_rms_threshold / 32768.0

    frames: list[np.ndarray] = []
    heard_speech = False
    last_speech_at = time.monotonic()
    started_at = time.monotonic()

    stream = sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        blocksize=FRAME_SAMPLES,
        device=device,
    )
    stream.start()
    try:
        while not stop_event.is_set():
            data, _overflow = stream.read(FRAME_SAMPLES)
            block = np.asarray(data, dtype=np.float32).reshape(-1)
            frames.append(block.copy())

            level = rms_level(block)
            if on_level is not None:
                on_level(min(1.0, level * 4.0))  # slight visual boost

            if endpointer is not None:
                speech = endpointer.is_speech(block)
            else:
                speech = level >= float_threshold

            now = time.monotonic()
            if speech:
                heard_speech = True
                last_speech_at = now

            if heard_speech and now - last_speech_at >= silence_seconds:
                log.info("Auto-stopped on silence")
                break
            if now - started_at >= max_seconds:
                log.info("Auto-stopped at max duration (%.0fs)", max_seconds)
                break
    finally:
        try:
            stream.stop()
            stream.close()
        except Exception:  # noqa: BLE001
            pass

    if not frames:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(frames).astype(np.float32)
