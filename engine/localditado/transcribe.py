"""Transcription engine: faster-whisper (primary) with Vosk fallback.

Accuracy/speed features:
- model resolved automatically (``large-v3-turbo`` when hardware allows);
- ``BatchedInferencePipeline`` for much higher throughput;
- ``hotwords`` to bias user-domain terms;
- in-memory input (numpy), no WAV on disk;
- optional pre-processing (normalisation + noise reduction).
"""

from __future__ import annotations

import ctypes
import logging
import os
import site
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from . import hardware, paths

log = logging.getLogger("localditado.transcribe")


def _configure_huggingface_environment() -> None:
    """Keep Hugging Face downloads quiet and predictable in the desktop app."""
    # Windows without Developer Mode cannot create Hugging Face cache symlinks.
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    # The bundled sidecar does not need Xet; regular HTTP download is simpler.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    # Keep optional download/auth hints out of the app terminal; errors still surface.
    os.environ.setdefault("HF_HUB_VERBOSITY", "error")


def _configure_nvidia_dll_paths() -> None:
    """On Windows, expose CUDA DLLs installed via pip (cuBLAS/cuDNN/runtime)."""
    if sys.platform != "win32":
        return
    roots = [Path(p) / "nvidia" for p in (*site.getsitepackages(), site.getusersitepackages())]
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        roots.insert(0, Path(frozen_root) / "nvidia")
    subdirs = ("cublas/bin", "cudnn/bin", "cuda_runtime/bin", "cuda_nvrtc/bin")
    for root in roots:
        for sub in subdirs:
            candidate = root / sub
            if candidate.exists():
                os.add_dll_directory(str(candidate))
                os.environ["PATH"] = str(candidate) + os.pathsep + os.environ.get("PATH", "")


_configure_huggingface_environment()
_configure_nvidia_dll_paths()


def _cuda_runtime_available() -> bool:
    """Return whether the CUDA DLLs needed by CTranslate2 can be loaded."""
    if sys.platform != "win32":
        return True
    for dll in ("cublas64_12.dll", "cudnn64_9.dll"):
        try:
            ctypes.WinDLL(dll)
        except OSError:
            log.warning("CUDA requested but %s is not loadable; falling back to CPU.", dll)
            return False
    return True


def _is_cuda_runtime_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(token in message for token in ("cublas", "cudnn", "cuda", "cublas64_12"))

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


class Backend(Protocol):
    """Common interface every transcription backend must expose.

    New backends (Parakeet, MLX on macOS, OpenVINO on Intel, …) only need to
    implement this and register a builder in ``BACKEND_BUILDERS`` — no caller
    changes required. ``device``/``model_name`` are used by diagnostics and the
    CUDA→CPU recovery path.
    """

    device: str
    model_name: str

    def transcribe(
        self,
        audio: np.ndarray,
        *,
        language: str | None = "pt",
        beam_size: int = 5,
        hotwords: str | None = None,
        initial_prompt: str | None = None,
        vad_filter: bool = True,
    ) -> tuple[str, str, float]: ...

    def warmup(self, language: str | None = "pt") -> None: ...


_df_cache: dict[str, object] = {}


def _denoise_spectral(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Spectral-gating noise reduction (noisereduce). Light, CPU-friendly."""
    try:
        import noisereduce as nr

        return nr.reduce_noise(y=audio, sr=sample_rate).astype(np.float32)
    except Exception as exc:  # noqa: BLE001
        log.warning("Noise reduction unavailable (%s); skipping.", exc)
        return audio


def _denoise_deepfilternet(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Deep real-time noise suppression (DeepFilterNet). Much stronger in noisy
    environments. Runs at 48 kHz, so we resample around it. The model is loaded
    once and cached. Falls back to the input on any failure.
    """
    try:
        import torch
        import torchaudio
        from df.enhance import enhance, init_df

        cached = _df_cache.get("model")
        if cached is None:
            model, df_state, _ = init_df()
            cached = (model, df_state)
            _df_cache["model"] = cached
        model, df_state = cached  # type: ignore[misc]
        df_sr = int(df_state.sr())

        sig = torch.from_numpy(audio.astype(np.float32)).unsqueeze(0)
        if sample_rate != df_sr:
            sig = torchaudio.functional.resample(sig, sample_rate, df_sr)
        enhanced = enhance(model, df_state, sig)
        if sample_rate != df_sr:
            enhanced = torchaudio.functional.resample(enhanced, df_sr, sample_rate)
        return enhanced.squeeze(0).cpu().numpy().astype(np.float32)
    except Exception as exc:  # noqa: BLE001
        log.warning("DeepFilterNet unavailable (%s); skipping.", exc)
        return audio


def preprocess_audio(
    audio: np.ndarray, sample_rate: int, denoise: bool, method: str = "spectral"
) -> np.ndarray:
    """Normalise and optionally reduce noise before transcribing."""
    if audio.size == 0:
        return audio
    audio = audio.astype(np.float32)

    if denoise:
        if method == "deepfilternet":
            audio = _denoise_deepfilternet(audio, sample_rate)
        else:
            audio = _denoise_spectral(audio, sample_rate)

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

    def warmup(self, language: str | None = "pt") -> None:
        """Run a short silent inference so cuDNN/CT2 autotune happens before the
        first real dictation. Without this, the first utterance pays a one-off
        latency spike (graph build, kernel autotune) that feels like a freeze.
        """
        try:
            silence = np.zeros(16000, dtype=np.float32)
            self.transcribe(silence, language=language, beam_size=1)
            log.info("Whisper warmup complete")
        except Exception:  # noqa: BLE001
            log.warning("Whisper warmup failed; first dictation may be slower.", exc_info=True)

    def transcribe(
        self,
        audio: np.ndarray,
        *,
        language: str | None = "pt",
        beam_size: int = 5,
        hotwords: str | None = None,
        initial_prompt: str | None = None,
        vad_filter: bool = True,
    ) -> tuple[str, str, float]:
        kwargs = dict(
            language=None if (language in (None, "auto")) else language,
            beam_size=beam_size,
            vad_filter=vad_filter,
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

    device = "cpu"
    model_name = "vosk"

    def __init__(self, model_path: str, sample_rate: int = 16000) -> None:
        from vosk import KaldiRecognizer, Model, SetLogLevel

        SetLogLevel(-1)
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Vosk model not found: {model_path}")
        self.model = Model(model_path)
        self.sample_rate = sample_rate
        self._recognizer_cls = KaldiRecognizer

    def warmup(self, language: str | None = "pt") -> None:  # noqa: D102 - no autotune cost
        return None

    def transcribe(self, audio: np.ndarray, **_: object) -> tuple[str, str, float]:
        import json

        pcm16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
        rec = self._recognizer_cls(self.model, self.sample_rate)
        rec.AcceptWaveform(pcm16)
        result = json.loads(rec.FinalResult())
        return result.get("text", "").strip(), "pt", 1.0


class ParakeetTranscriber:
    """NVIDIA NeMo Parakeet (TDT) backend — multilingual, very fast on CUDA.

    Optional: needs the ``[parakeet]`` extra (``nemo_toolkit[asr]``). The heavy
    import stays inside ``__init__`` so the package loads without NeMo present.
    Parakeet does not take a text prompt, so ``hotwords``/``initial_prompt`` are
    accepted for interface parity but ignored.
    """

    def __init__(
        self, model_name: str = "nvidia/parakeet-tdt-0.6b-v3", download_root: str | None = None
    ) -> None:
        import nemo.collections.asr as nemo_asr  # lazy, heavy optional dependency

        self.model_name = model_name
        log.info("Loading Parakeet %s", model_name)
        self._model = nemo_asr.models.ASRModel.from_pretrained(model_name)
        try:
            import torch

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:  # noqa: BLE001
            self.device = "cpu"
        log.info("Parakeet loaded (device=%s)", self.device)

    def warmup(self, language: str | None = "pt") -> None:  # noqa: D102
        try:
            self.transcribe(np.zeros(16000, dtype=np.float32))
            log.info("Parakeet warmup complete")
        except Exception:  # noqa: BLE001
            log.warning("Parakeet warmup failed; first dictation may be slower.", exc_info=True)

    def transcribe(
        self,
        audio: np.ndarray,
        *,
        language: str | None = "pt",
        beam_size: int = 1,
        hotwords: str | None = None,
        initial_prompt: str | None = None,
        vad_filter: bool = True,
    ) -> tuple[str, str, float]:
        # NeMo expects 16 kHz mono float32; recent versions accept numpy arrays.
        outputs = self._model.transcribe([audio.astype(np.float32)], batch_size=1, verbose=False)
        hyp = outputs[0] if outputs else ""
        # Depending on the model, NeMo returns Hypothesis objects or plain strings.
        text = getattr(hyp, "text", hyp)
        return str(text).strip(), (language or "pt"), 1.0


def _build_whisper(settings: dict) -> tuple[Backend, str, str]:
    if WhisperModel is None:
        raise RuntimeError("faster-whisper is not installed.")
    model, device, compute_type = hardware.resolve(settings)
    if device == "cuda" and not _cuda_runtime_available():
        device, compute_type = "cpu", "int8"
    backend = WhisperTranscriber(
        model,
        device,
        compute_type,
        cpu_threads=int(settings.get("cpu_threads", 0) or 0),
        batched=bool(settings.get("batched", True)),
        batch_size=int(settings.get("batch_size", 8)),
        download_root=str(paths.models_dir()),
    )
    return backend, "whisper", model


def _build_parakeet(settings: dict) -> tuple[Backend, str, str]:
    model_name = str(settings.get("parakeet_model", "nvidia/parakeet-tdt-0.6b-v3"))
    backend = ParakeetTranscriber(model_name, download_root=str(paths.models_dir()))
    return backend, "parakeet", model_name


def _build_vosk(settings: dict) -> tuple[Backend, str, str]:
    backend = VoskTranscriber(
        str(settings.get("vosk_model")), int(settings.get("sample_rate", 16000))
    )
    return backend, "vosk", "vosk"


# Register a builder here to add a backend; callers never branch on engine type.
BackendBuilder = Callable[[dict], tuple[Backend, str, str]]
BACKEND_BUILDERS: dict[str, BackendBuilder] = {
    "whisper": _build_whisper,
    "parakeet": _build_parakeet,
    "vosk": _build_vosk,
}


class Engine:
    """Facade that builds the requested backend and exposes ``transcribe``.

    Selection order: the requested ``engine`` first, then Whisper, then Vosk —
    so a missing optional backend degrades gracefully instead of crashing.
    """

    def __init__(self, settings: dict) -> None:
        self.settings = settings
        self.kind = "whisper"
        self.model_name = "?"
        self.backend: Backend
        self._build()

    def _build(self) -> None:
        requested = str(self.settings.get("engine", "whisper"))
        order = [requested] + [name for name in ("whisper", "vosk") if name != requested]
        last_error: Exception | None = None
        for name in order:
            builder = BACKEND_BUILDERS.get(name)
            if builder is None:
                continue
            try:
                self.backend, self.kind, self.model_name = builder(self.settings)
                if self.settings.get("warmup", True):
                    self.backend.warmup(self.settings.get("language", "pt"))
                return
            except Exception as exc:  # noqa: BLE001
                log.exception("Backend '%s' unavailable; trying next.", name)
                last_error = exc
        raise RuntimeError("No transcription backend could be loaded.") from last_error

    def transcribe(
        self, audio: np.ndarray, initial_prompt: str | None = None
    ) -> TranscriptionResult:
        import time

        s = self.settings
        sr = int(s.get("sample_rate", 16000))
        audio = preprocess_audio(
            audio, sr, bool(s.get("denoise", False)), str(s.get("denoise_method", "spectral"))
        )
        started = time.perf_counter()
        kwargs = {
            "language": s.get("language", "pt"),
            "beam_size": int(s.get("beam_size", 5)),
            "hotwords": str(s.get("hotwords", "")) or None,
            "initial_prompt": initial_prompt,
        }
        try:
            text, lang, prob = self.backend.transcribe(audio, **kwargs)
        except RuntimeError as exc:
            if not (
                isinstance(self.backend, WhisperTranscriber)
                and self.backend.device == "cuda"
                and _is_cuda_runtime_error(exc)
            ):
                raise
            log.exception("CUDA transcription failed; rebuilding Whisper on CPU and retrying.")
            self.backend = WhisperTranscriber(
                self.backend.model_name,
                "cpu",
                "int8",
                cpu_threads=int(s.get("cpu_threads", 0) or 0),
                batched=bool(s.get("batched", True)),
                batch_size=int(s.get("batch_size", 8)),
                download_root=str(paths.models_dir()),
            )
            text, lang, prob = self.backend.transcribe(audio, **kwargs)
        return TranscriptionResult(
            text=text,
            language=lang,
            language_probability=prob,
            elapsed=time.perf_counter() - started,
            engine=self.kind,
            model=self.model_name,
        )
