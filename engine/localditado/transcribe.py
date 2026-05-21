"""Transcription engine: faster-whisper (primary) with Vosk fallback.

Accuracy/speed features:
- model resolved automatically (``large-v3-turbo`` when hardware allows);
- ``BatchedInferencePipeline`` for much higher throughput;
- ``hotwords`` to bias user-domain terms;
- in-memory input (numpy), no WAV on disk;
- optional pre-processing (normalisation + noise reduction).
"""

from __future__ import annotations

import logging
import os
import site
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import hardware

log = logging.getLogger("localditado.transcribe")


def _configure_nvidia_dll_paths() -> None:
    """On Windows, expose CUDA DLLs installed via pip (cuBLAS/cuDNN/runtime)."""
    if sys.platform != "win32":
        return
    roots = [Path(p) / "nvidia" for p in (*site.getsitepackages(), site.getusersitepackages())]
    subdirs = ("cublas/bin", "cudnn/bin", "cuda_runtime/bin", "cuda_nvrtc/bin")
    for root in roots:
        for sub in subdirs:
            candidate = root / sub
            if candidate.exists():
                os.add_dll_directory(str(candidate))
                os.environ["PATH"] = str(candidate) + os.pathsep + os.environ.get("PATH", "")


_configure_nvidia_dll_paths()

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None  # type: ignore[assignment]

try:
    from faster_whisper import BatchedInferencePipeline
except ImportError:
    BatchedInferencePipeline = None  # type: ignore[assignment]


@dataclass
class TranscriptionResult:
    text: str
    language: str
    language_probability: float
    elapsed: float
    engine: str
    model: str


def preprocess_audio(audio: np.ndarray, sample_rate: int, denoise: bool) -> np.ndarray:
    """Normalise and optionally reduce noise before transcribing."""
    if audio.size == 0:
        return audio
    audio = audio.astype(np.float32)

    if denoise:
        try:
            import noisereduce as nr

            audio = nr.reduce_noise(y=audio, sr=sample_rate).astype(np.float32)
        except Exception as exc:  # noqa: BLE001
            log.warning("Noise reduction unavailable (%s); skipping.", exc)

    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0:
        audio = (audio / peak) * 0.95
    return audio


class WhisperTranscriber:
    def __init__(
        self,
        model_name: str,
        device: str,
        compute_type: str,
        cpu_threads: int = 0,
        batched: bool = True,
        batch_size: int = 8,
        download_root: str | None = None,
    ) -> None:
        if WhisperModel is None:
            raise RuntimeError("faster-whisper is not installed.")
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        log.info("Loading Whisper %s device=%s ct=%s", model_name, device, compute_type)
        self.model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            cpu_threads=cpu_threads or 0,
            download_root=download_root,
        )
        self.batched = batched and BatchedInferencePipeline is not None
        self.pipeline = BatchedInferencePipeline(model=self.model) if self.batched else None
        log.info("Whisper loaded (batched=%s)", self.batched)

    def transcribe(
        self,
        audio: np.ndarray,
        *,
        language: str | None = "pt",
        beam_size: int = 5,
        hotwords: str | None = None,
        initial_prompt: str | None = None,
    ) -> tuple[str, str, float]:
        kwargs = dict(
            language=None if (language in (None, "auto")) else language,
            beam_size=beam_size,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=initial_prompt,
            hotwords=hotwords or None,
        )
        if self.pipeline is not None:
            segments, info = self.pipeline.transcribe(audio, batch_size=self.batch_size, **kwargs)
        else:
            segments, info = self.model.transcribe(audio, **kwargs)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        lang = getattr(info, "language", language or "pt")
        prob = float(getattr(info, "language_probability", 0.0))
        return text, lang, prob


class VoskTranscriber:
    """Offline fallback. Transcribes from a float32 array in memory."""

    def __init__(self, model_path: str, sample_rate: int = 16000) -> None:
        from vosk import KaldiRecognizer, Model, SetLogLevel

        SetLogLevel(-1)
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Vosk model not found: {model_path}")
        self.model = Model(model_path)
        self.sample_rate = sample_rate
        self._recognizer_cls = KaldiRecognizer

    def transcribe(self, audio: np.ndarray, **_: object) -> tuple[str, str, float]:
        import json

        pcm16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
        rec = self._recognizer_cls(self.model, self.sample_rate)
        rec.AcceptWaveform(pcm16)
        result = json.loads(rec.FinalResult())
        return result.get("text", "").strip(), "pt", 1.0


class Engine:
    """Facade that selects Whisper (with Vosk fallback) and exposes ``transcribe``."""

    def __init__(self, settings: dict) -> None:
        self.settings = settings
        self.kind = "whisper"
        self.model_name = "?"
        self._build()

    def _build(self) -> None:
        from . import paths

        engine = str(self.settings.get("engine", "whisper"))
        if engine == "whisper" and WhisperModel is not None:
            model, device, compute_type = hardware.resolve(self.settings)
            try:
                self.backend: WhisperTranscriber | VoskTranscriber = WhisperTranscriber(
                    model,
                    device,
                    compute_type,
                    cpu_threads=int(self.settings.get("cpu_threads", 0) or 0),
                    batched=bool(self.settings.get("batched", True)),
                    batch_size=int(self.settings.get("batch_size", 8)),
                    download_root=str(paths.models_dir()),
                )
                self.kind = "whisper"
                self.model_name = model
                return
            except Exception:
                log.exception("Failed to load Whisper; trying Vosk.")

        self.backend = VoskTranscriber(
            str(self.settings.get("vosk_model")),
            int(self.settings.get("sample_rate", 16000)),
        )
        self.kind = "vosk"
        self.model_name = "vosk"

    def transcribe(
        self, audio: np.ndarray, initial_prompt: str | None = None
    ) -> TranscriptionResult:
        import time

        s = self.settings
        sr = int(s.get("sample_rate", 16000))
        audio = preprocess_audio(audio, sr, bool(s.get("denoise", False)))
        started = time.perf_counter()
        text, lang, prob = self.backend.transcribe(
            audio,
            language=s.get("language", "pt"),
            beam_size=int(s.get("beam_size", 5)),
            hotwords=str(s.get("hotwords", "")) or None,
            initial_prompt=initial_prompt,
        )
        return TranscriptionResult(
            text=text,
            language=lang,
            language_probability=prob,
            elapsed=time.perf_counter() - started,
            engine=self.kind,
            model=self.model_name,
        )
