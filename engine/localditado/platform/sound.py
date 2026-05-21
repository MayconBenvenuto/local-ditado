"""Cross-platform audio feedback.

Generates short tones with numpy and plays them via sounddevice — replaces ``winsound``
and works on Windows, Linux, and macOS. Fully fail-safe: if no audio output is available,
it silences gracefully.
"""

from __future__ import annotations

import logging
import threading

import numpy as np

log = logging.getLogger("localditado.sound")

_SAMPLE_RATE = 44100
_enabled = True


def set_enabled(enabled: bool) -> None:
    global _enabled
    _enabled = enabled


def _tone(freq: float, duration: float, volume: float = 0.3) -> np.ndarray:
    t = np.linspace(0, duration, int(_SAMPLE_RATE * duration), endpoint=False)
    wave = np.sin(2 * np.pi * freq * t) * volume
    # Fade envelope to avoid click at start/end.
    fade = int(_SAMPLE_RATE * 0.008)
    if fade > 0 and wave.size > 2 * fade:
        ramp = np.linspace(0, 1, fade)
        wave[:fade] *= ramp
        wave[-fade:] *= ramp[::-1]
    return wave.astype(np.float32)


def _play_async(wave: np.ndarray) -> None:
    if not _enabled:
        return

    def _worker() -> None:
        try:
            import sounddevice as sd

            sd.play(wave, _SAMPLE_RATE)
            sd.wait()
        except Exception as exc:  # noqa: BLE001
            log.debug("Sem feedback sonoro: %s", exc)

    threading.Thread(target=_worker, daemon=True).start()


def beep_start() -> None:
    _play_async(_tone(880, 0.12))


def beep_stop() -> None:
    _play_async(_tone(520, 0.12))


def beep_error() -> None:
    _play_async(_tone(220, 0.30))
