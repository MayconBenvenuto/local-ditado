"""Resident dictation service.

Wires everything together: global hotkey → in-memory capture → endpointing (VAD) →
transcription → post-processing → paste into the focused app. Emits events to the
interface (status, microphone level, result) via callback.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import numpy as np

from . import audio, history, paths, postprocess, transcribe, vad
from .platform import paste, sound

log = logging.getLogger("localditado.service")

EventCallback = Callable[[str, dict], None]


class DictationService:
    def __init__(self, settings: dict, on_event: EventCallback | None = None) -> None:
        self.settings = settings
        self.on_event = on_event or (lambda _e, _p: None)
        self.lock = threading.Lock()
        self.recording_thread: threading.Thread | None = None
        self.stop_event: threading.Event | None = None

        sound.set_enabled(bool(settings.get("feedback_sound", True)))
        self.initial_prompt = self._load_prompt()
        self._endpointer = vad.make_endpointer(
            str(settings.get("vad", "silero")),
            sample_rate=int(settings.get("sample_rate", 16000)),
            speech_rms_threshold=float(settings.get("speech_rms_threshold", 450)),
        )
        # Load the model at boot so the first dictation is fast.
        self.engine = transcribe.Engine(settings)
        self.emit("ready", {"engine": self.engine.kind, "model": self.engine.model_name})

    # ------------------------------------------------------------------
    def emit(self, event: str, payload: dict | None = None) -> None:
        try:
            self.on_event(event, payload or {})
        except Exception:  # noqa: BLE001
            log.exception("Erro no callback de evento")

    def _load_prompt(self) -> str | None:
        prompt_file = self.settings.get("initial_prompt_file")
        if prompt_file and Path(prompt_file).exists():
            return Path(prompt_file).read_text(encoding="utf-8").strip()
        return None

    @property
    def is_recording(self) -> bool:
        return bool(self.recording_thread and self.recording_thread.is_alive())

    # ------------------------------------------------------------------
    def toggle(self) -> None:
        with self.lock:
            if self.is_recording:
                log.info("Parando ditado (manual)")
                if self.stop_event:
                    self.stop_event.set()
                return
            self.stop_event = threading.Event()
            self.recording_thread = threading.Thread(
                target=self._run_cycle, args=(self.stop_event,), daemon=True
            )
            self.recording_thread.start()

    def stop(self) -> None:
        if self.stop_event:
            self.stop_event.set()

    # ------------------------------------------------------------------
    def _run_cycle(self, stop_event: threading.Event) -> None:
        try:
            sound.beep_start()
            self.emit("recording_started", {})
            device = audio.resolve_device_index(
                self.settings.get("device"),
                self.settings.get("device_name"),
                int(self.settings.get("sample_rate", 16000)),
            )
            samples = audio.record_until_stop(
                stop_event,
                device=device,
                sample_rate=int(self.settings.get("sample_rate", 16000)),
                silence_seconds=float(self.settings.get("silence_seconds", 1.5)),
                max_seconds=float(self.settings.get("max_seconds", 120)),
                endpointer=self._endpointer,
                speech_rms_threshold=float(self.settings.get("speech_rms_threshold", 450)),
                on_level=lambda lvl: self.emit("level", {"level": lvl}),
            )
            sound.beep_stop()

            if samples.size == 0:
                self.emit("result", {"text": "", "empty": True})
                return

            if self.settings.get("save_recordings"):
                self._save_recording(samples)

            self.emit("transcribing", {})
            result = self.engine.transcribe(samples, initial_prompt=self.initial_prompt)
            text = postprocess.process_with_settings(result.text, self.settings)

            if self.settings.get("llm_format") and text:
                from . import llm_postprocess

                text = llm_postprocess.format_text(text, self.settings)

            if self.settings.get("save_transcript", True) and text:
                history.append_entry(
                    text,
                    {
                        "engine": result.engine,
                        "model": result.model,
                        "elapsed": round(result.elapsed, 2),
                        "language": result.language,
                    },
                )

            if self.settings.get("auto_paste", True) and text:
                paste.paste_text(text)

            sr = int(self.settings.get("sample_rate", 16000))
            self.emit(
                "result",
                {
                    "text": text,
                    "elapsed": round(result.elapsed, 2),
                    "engine": result.engine,
                    "model": result.model,
                    "audio_seconds": round(samples.size / sr, 1),
                },
            )
            log.info(
                "Ditado: %d chars em %.2fs (%s/%s)",
                len(text), result.elapsed, result.engine, result.model,
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("Erro no ciclo de ditado")
            sound.beep_error()
            self.emit("error", {"message": str(exc)})

    def _save_recording(self, samples: np.ndarray) -> None:
        import wave

        try:
            rec_dir = paths.recordings_dir()
            self._prune_recordings(rec_dir)
            wav_path = rec_dir / f"dictado-{datetime.now().strftime('%Y%m%d-%H%M%S')}.wav"
            pcm16 = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
            with wave.open(str(wav_path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(int(self.settings.get("sample_rate", 16000)))
                wav.writeframes(pcm16.tobytes())
        except Exception:  # noqa: BLE001
            log.exception("Failed to save recording")

    def _prune_recordings(self, rec_dir: Path) -> None:
        retention_days = int(self.settings.get("recordings_retention_days", 7))
        if retention_days <= 0:
            return
        cutoff = time.time() - retention_days * 86400
        for wav in rec_dir.glob("dictado-*.wav"):
            try:
                if wav.stat().st_mtime < cutoff:
                    wav.unlink()
            except OSError:
                pass
