import argparse
import ctypes
import json
import logging
import os
import site
import threading
import time
import wave
from array import array
from datetime import datetime
from pathlib import Path

import pyaudio
import winsound
from vosk import KaldiRecognizer, Model, SetLogLevel


def configure_nvidia_dll_paths() -> list[str]:
    dll_dirs: list[str] = []
    candidates: list[Path] = []
    for site_dir in site.getsitepackages() + [site.getusersitepackages()]:
        root = Path(site_dir) / "nvidia"
        candidates.extend(
            [
                root / "cublas" / "bin",
                root / "cudnn" / "bin",
                root / "cuda_runtime" / "bin",
                root / "cuda_nvrtc" / "bin",
            ]
        )

    for candidate in candidates:
        if not candidate.exists():
            continue
        os.add_dll_directory(str(candidate))
        os.environ["PATH"] = str(candidate) + os.pathsep + os.environ.get("PATH", "")
        dll_dirs.append(str(candidate))
    return dll_dirs


NVIDIA_DLL_DIRS = configure_nvidia_dll_paths()

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None


ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = ROOT / "models" / "vosk-model-small-pt-0.3"
LOG_PATH = ROOT / "dictado-hotkey.log"
TRANSCRIPT_PATH = ROOT / "ditado.txt"
RECORDINGS_DIR = ROOT / "recordings"
DEFAULT_PROMPT_PATH = ROOT / "prompts" / "pt-br-default.txt"
SAMPLE_RATE = 16000
DEFAULT_SILENCE_SECONDS_TO_AUTO_STOP = 2.5
SPEECH_RMS_THRESHOLD = 450

HOTKEY_ID = 1
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
VK_D = 0x44
WM_HOTKEY = 0x0312

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_V = 0x56

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = ctypes.c_int
user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
user32.SetClipboardData.restype = ctypes.c_void_p


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_void_p),
        ("lParam", ctypes.c_void_p),
        ("time", ctypes.c_ulong),
        ("pt", ctypes.c_long * 2),
    ]


def setup_logging() -> None:
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )


def beep_start() -> None:
    winsound.Beep(880, 120)


def beep_stop() -> None:
    winsound.Beep(520, 120)


def beep_error() -> None:
    winsound.Beep(220, 300)


def append_transcript(text: str) -> None:
    if not text.strip():
        return
    with TRANSCRIPT_PATH.open("a", encoding="utf-8") as file:
        file.write(f"\n--- Ditado {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        file.write(text.strip() + "\n")


def rms_level(data: bytes) -> int:
    samples = array("h")
    samples.frombytes(data)
    if not samples:
        return 0
    total = sum(sample * sample for sample in samples)
    return int((total / len(samples)) ** 0.5)


def set_clipboard_text(text: str) -> None:
    data = (text + "\0").encode("utf-16-le")
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not handle:
        raise ctypes.WinError()

    locked = kernel32.GlobalLock(handle)
    if not locked:
        raise ctypes.WinError()

    ctypes.memmove(locked, data, len(data))
    kernel32.GlobalUnlock(handle)

    if not user32.OpenClipboard(None):
        raise ctypes.WinError()
    try:
        if not user32.EmptyClipboard():
            raise ctypes.WinError()
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            raise ctypes.WinError()
    finally:
        user32.CloseClipboard()


def paste_text(target_hwnd: int, text: str) -> None:
    if not text.strip():
        return
    set_clipboard_text(text.strip())
    if target_hwnd:
        user32.SetForegroundWindow(target_hwnd)
        time.sleep(0.15)

    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_V, 0, 0, 0)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def find_input_device(pa: pyaudio.PyAudio, device_name: str | None) -> int | None:
    if not device_name:
        return None

    matches: list[tuple[int, int, str]] = []
    needle = device_name.lower()
    for index in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(index)
        channels = int(info.get("maxInputChannels", 0))
        name = str(info.get("name", ""))
        if channels <= 0 or needle not in name.lower():
            continue
        default_rate = int(info.get("defaultSampleRate", 0))
        score = 0 if default_rate == SAMPLE_RATE else abs(default_rate - SAMPLE_RATE)
        matches.append((score, index, name))

    if not matches:
        raise RuntimeError(f"Microfone nao encontrado pelo nome: {device_name}")

    matches.sort()
    _, index, name = matches[0]
    logging.info("Microfone selecionado por nome: %s (%s)", index, name)
    return index


def open_stream(pa: pyaudio.PyAudio, device_index: int | None, sample_rate: int):
    return pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=sample_rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=4000,
    )


class DictationService:
    def __init__(
        self,
        device_index: int | None,
        device_name: str | None,
        model_path: Path,
        engine: str,
        whisper_model: str,
        whisper_device: str,
        whisper_compute_type: str,
        silence_seconds: float,
        beam_size: int,
        cpu_threads: int,
        initial_prompt: str | None,
    ):
        self.device_index = device_index
        self.device_name = device_name
        self.model_path = model_path
        self.engine = engine
        self.whisper_model_name = whisper_model
        self.whisper_device = whisper_device
        self.whisper_compute_type = whisper_compute_type
        self.silence_seconds = silence_seconds
        self.beam_size = beam_size
        self.cpu_threads = cpu_threads
        self.initial_prompt = initial_prompt
        self.whisper_model = None
        self.vosk_model = None
        self.lock = threading.Lock()
        self.recording_thread: threading.Thread | None = None
        self.stop_event: threading.Event | None = None
        self.target_hwnd = 0

        SetLogLevel(-1)
        if self.engine == "whisper" and WhisperModel is not None:
            logging.info(
                "Carregando Whisper %s device=%s compute_type=%s",
                self.whisper_model_name,
                self.whisper_device,
                self.whisper_compute_type,
            )
            try:
                self.whisper_model = WhisperModel(
                    self.whisper_model_name,
                    device=self.whisper_device,
                    compute_type=self.whisper_compute_type,
                    cpu_threads=self.cpu_threads,
                )
                logging.info("Whisper carregado")
            except Exception:
                logging.exception("Falha ao carregar Whisper; usando Vosk como fallback")
                self.engine = "vosk"

        if self.engine == "vosk" or self.whisper_model is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Modelo Vosk nao encontrado: {self.model_path}")
            logging.info("Carregando Vosk em %s", self.model_path)
            self.vosk_model = Model(str(self.model_path))
            self.engine = "vosk"
            logging.info("Vosk carregado")

    def toggle(self) -> None:
        with self.lock:
            if self.recording_thread and self.recording_thread.is_alive():
                logging.info("Parando ditado")
                if self.stop_event:
                    self.stop_event.set()
                beep_stop()
                return

            logging.info("Iniciando ditado")
            self.target_hwnd = user32.GetForegroundWindow()
            self.stop_event = threading.Event()
            self.recording_thread = threading.Thread(
                target=self.record_with_selected_engine,
                args=(self.stop_event, self.target_hwnd),
                daemon=True,
            )
            self.recording_thread.start()
            beep_start()

    def resolve_device_index(self, pa: pyaudio.PyAudio) -> int | None:
        device_index = self.device_index
        if device_index is None:
            device_index = find_input_device(pa, self.device_name)
        if device_index is None:
            info = pa.get_default_input_device_info()
            logging.info("Microfone padrao selecionado: %s (%s)", info.get("index"), info.get("name"))
        else:
            info = pa.get_device_info_by_index(device_index)
            logging.info("Microfone selecionado: %s (%s)", device_index, info.get("name"))
        return device_index

    def record_with_selected_engine(self, stop_event: threading.Event, target_hwnd: int) -> None:
        if self.engine == "whisper" and self.whisper_model is not None:
            self.record_with_whisper(stop_event, target_hwnd)
        else:
            self.record_with_vosk(stop_event, target_hwnd)

    def record_audio_until_stop(self, stop_event: threading.Event) -> Path:
        pa = pyaudio.PyAudio()
        stream = None
        try:
            device_index = self.resolve_device_index(pa)
            stream = open_stream(pa, device_index, SAMPLE_RATE)
            frames: list[bytes] = []
            heard_speech = False
            last_speech_at = time.monotonic()

            while not stop_event.is_set():
                data = stream.read(4000, exception_on_overflow=False)
                frames.append(data)
                if rms_level(data) >= SPEECH_RMS_THRESHOLD:
                    heard_speech = True
                    last_speech_at = time.monotonic()

                if heard_speech and time.monotonic() - last_speech_at >= self.silence_seconds:
                    logging.info("Parando ditado automaticamente por silencio")
                    beep_stop()
                    break

            RECORDINGS_DIR.mkdir(exist_ok=True)
            wav_path = RECORDINGS_DIR / f"dictado-{datetime.now().strftime('%Y%m%d-%H%M%S')}.wav"
            with wave.open(str(wav_path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
                wav.setframerate(SAMPLE_RATE)
                wav.writeframes(b"".join(frames))
            return wav_path
        finally:
            if stream is not None:
                try:
                    if stream.is_active():
                        stream.stop_stream()
                    stream.close()
                except OSError:
                    pass
            pa.terminate()

    def record_with_whisper(self, stop_event: threading.Event, target_hwnd: int) -> None:
        try:
            wav_path = self.record_audio_until_stop(stop_event)
            logging.info("Transcrevendo com Whisper: %s", wav_path)
            started_at = time.perf_counter()
            segments, info = self.whisper_model.transcribe(
                str(wav_path),
                language="pt",
                beam_size=self.beam_size,
                vad_filter=True,
                condition_on_previous_text=False,
                initial_prompt=self.initial_prompt,
            )
            final_text = " ".join(segment.text.strip() for segment in segments).strip()
            elapsed = time.perf_counter() - started_at
            append_transcript(final_text)
            paste_text(target_hwnd, final_text)
            logging.info(
                "Ditado Whisper finalizado: %s caracteres em %.2fs, idioma=%s prob=%.2f",
                len(final_text),
                elapsed,
                getattr(info, "language", "pt"),
                getattr(info, "language_probability", 0.0),
            )
        except Exception:
            logging.exception("Erro no ditado Whisper")
            beep_error()

    def record_with_vosk(self, stop_event: threading.Event, target_hwnd: int) -> None:
        pa = pyaudio.PyAudio()
        stream = None
        try:
            device_index = self.resolve_device_index(pa)
            stream = open_stream(pa, device_index, SAMPLE_RATE)
            recognizer = KaldiRecognizer(self.vosk_model, SAMPLE_RATE)
            chunks: list[str] = []

            while not stop_event.is_set():
                data = stream.read(4000, exception_on_overflow=False)
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        chunks.append(text)

            result = json.loads(recognizer.FinalResult())
            text = result.get("text", "").strip()
            if text:
                chunks.append(text)

            final_text = " ".join(chunks).strip()
            append_transcript(final_text)
            paste_text(target_hwnd, final_text)
            logging.info("Ditado finalizado: %s caracteres", len(final_text))
        except Exception:
            logging.exception("Erro no ditado")
            beep_error()
        finally:
            if stream is not None:
                try:
                    if stream.is_active():
                        stream.stop_stream()
                    stream.close()
                except OSError:
                    pass
            pa.terminate()


def register_hotkey() -> None:
    if not user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_ALT, VK_D):
        raise ctypes.WinError()


def unregister_hotkey() -> None:
    user32.UnregisterHotKey(None, HOTKEY_ID)


def message_loop(service: DictationService) -> None:
    msg = MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
            service.toggle()
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Servico de ditado local com hotkey.")
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Indice do microfone. Sem valor, usa o microfone padrao do Windows.",
    )
    parser.add_argument(
        "--device-name",
        default=None,
        help="Trecho do nome do microfone. Exemplo: External Mic.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="Pasta do modelo Vosk.",
    )
    parser.add_argument(
        "--engine",
        choices=("whisper", "vosk"),
        default="vosk",
        help="Motor de transcricao.",
    )
    parser.add_argument(
        "--whisper-model",
        default="small",
        help="Modelo do faster-whisper. Exemplo: small, medium.",
    )
    parser.add_argument(
        "--whisper-device",
        default="cpu",
        help="Dispositivo do faster-whisper: cpu, cuda ou auto.",
    )
    parser.add_argument(
        "--whisper-compute-type",
        default="int8",
        help="Precisao do faster-whisper. Use int8 para CPU.",
    )
    parser.add_argument(
        "--silence-seconds",
        type=float,
        default=DEFAULT_SILENCE_SECONDS_TO_AUTO_STOP,
        help="Segundos de silencio para finalizar automaticamente.",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Beam size do Whisper. 5 tende a ser mais preciso; 1 pode ser mais rapido.",
    )
    parser.add_argument(
        "--cpu-threads",
        type=int,
        default=8,
        help="Threads de CPU para o Whisper.",
    )
    parser.add_argument(
        "--initial-prompt-file",
        type=Path,
        default=DEFAULT_PROMPT_PATH,
        help="Arquivo de prompt de contexto para melhorar a transcricao.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    setup_logging()

    model_path = args.model.resolve()
    if not model_path.exists() and args.engine == "vosk":
        logging.error("Modelo Vosk nao encontrado: %s", model_path)
        beep_error()
        return 2
    if not model_path.exists() and args.engine == "whisper":
        logging.warning("Modelo Vosk fallback nao encontrado: %s", model_path)

    initial_prompt = None
    if args.initial_prompt_file and args.initial_prompt_file.exists():
        initial_prompt = args.initial_prompt_file.read_text(encoding="utf-8").strip()
        logging.info("Prompt de contexto carregado: %s", args.initial_prompt_file)

    service = DictationService(
        device_index=args.device,
        device_name=args.device_name,
        model_path=model_path,
        engine=args.engine,
        whisper_model=args.whisper_model,
        whisper_device=args.whisper_device,
        whisper_compute_type=args.whisper_compute_type,
        silence_seconds=args.silence_seconds,
        beam_size=args.beam_size,
        cpu_threads=args.cpu_threads,
        initial_prompt=initial_prompt,
    )
    register_hotkey()
    logging.info("Servico ativo. Atalho: Ctrl+Alt+D")
    beep_start()
    try:
        message_loop(service)
    finally:
        unregister_hotkey()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
