"""Endpointing (end-of-speech detection).

``SileroEndpointer`` uses the Silero VAD neural model to decide, block by block,
whether there is speech — much more robust than an energy threshold in noisy environments.
If Silero is not installed, fall back to ``RmsEndpointer``.
"""

from __future__ import annotations

import logging

import numpy as np

log = logging.getLogger("localditado.vad")


class RmsEndpointer:
    """Simple energy (RMS) fallback endpointer on float32 blocks."""

    def __init__(self, threshold_int16: float = 450.0) -> None:
        self.threshold = threshold_int16 / 32768.0

    def reset(self) -> None:  # noqa: D102
        return None

    def is_speech(self, frame: np.ndarray) -> bool:  # noqa: D102
        if frame.size == 0:
            return False
        return float(np.sqrt(np.mean(np.square(frame, dtype=np.float64)))) >= self.threshold


class SileroEndpointer:
    """Neural endpointer based on Silero VAD (512-sample blocks at 16 kHz)."""

    def __init__(self, sample_rate: int = 16000, threshold: float = 0.5) -> None:
        from silero_vad import load_silero_vad  # lazy import (optional dependency)

        self.sample_rate = sample_rate
        self.threshold = threshold
        self.model = load_silero_vad(onnx=True)

    def reset(self) -> None:  # noqa: D102
        try:
            self.model.reset_states()
        except Exception:  # noqa: BLE001
            pass

    def is_speech(self, frame: np.ndarray) -> bool:  # noqa: D102
        import torch

        if frame.size < 512:
            frame = np.pad(frame, (0, 512 - frame.size))
        elif frame.size > 512:
            frame = frame[:512]
        tensor = torch.from_numpy(frame.astype(np.float32))
        with torch.no_grad():
            prob = float(self.model(tensor, self.sample_rate).item())
        return prob >= self.threshold


def make_endpointer(kind: str, *, sample_rate: int, speech_rms_threshold: float):
    """Create the requested endpointer with automatic fallback to RMS."""
    if kind == "silero":
        try:
            ep = SileroEndpointer(sample_rate=sample_rate)
            log.info("Endpointing: Silero VAD")
            return ep
        except Exception as exc:  # noqa: BLE001
            log.warning("Silero VAD unavailable (%s); using RMS.", exc)
    return RmsEndpointer(threshold_int16=speech_rms_threshold)
