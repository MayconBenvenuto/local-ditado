import argparse
import json
import os
import subprocess
import sys
from array import array
from datetime import datetime
from pathlib import Path

import pyaudio
from vosk import KaldiRecognizer, Model, SetLogLevel


ROOT = Path(__file__).resolve().parent
BIG_MODEL = ROOT / "models" / "vosk-model-pt-fb-v0.1.1-20220516_2113"
SMALL_MODEL = ROOT / "models" / "vosk-model-small-pt-0.3"
DEFAULT_MODEL = BIG_MODEL if BIG_MODEL.exists() else SMALL_MODEL
DEFAULT_OUTPUT = ROOT / "ditado.txt"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ditado local offline com Vosk e microfone.",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="Lista dispositivos de entrada e sai.",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Indice do microfone. Use --list-devices para ver as opcoes.",
    )
    parser.add_argument(
        "--device-name",
        default=None,
        help="Trecho do nome do microfone. Exemplo: External Mic.",
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=16000,
        help="Taxa de amostragem desejada. Se falhar, o script tenta a taxa padrao do microfone.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL,
        help="Pasta do modelo Vosk.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Arquivo onde o ditado sera salvo.",
    )
    parser.add_argument(
        "--clipboard",
        action="store_true",
        help="Copia o texto final para a area de transferencia ao sair.",
    )
    parser.add_argument(
        "--test-seconds",
        type=float,
        default=0,
        help="Testa o nivel do microfone por alguns segundos e sai.",
    )
    return parser


def list_input_devices(pa: pyaudio.PyAudio) -> None:
    print("Microfones encontrados:")
    for index in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(index)
        channels = int(info.get("maxInputChannels", 0))
        if channels <= 0:
            continue
        rate = int(info.get("defaultSampleRate", 0))
        print(f"  {index}: {info.get('name')} | canais={channels} | padrao={rate} Hz")


def resolve_rate(pa: pyaudio.PyAudio, device_index: int | None, requested_rate: int) -> int:
    if device_index is None:
        info = pa.get_default_input_device_info()
    else:
        info = pa.get_device_info_by_index(device_index)

    try:
        pa.is_format_supported(
            requested_rate,
            input_device=device_index,
            input_channels=1,
            input_format=pyaudio.paInt16,
        )
        return requested_rate
    except ValueError:
        return int(info.get("defaultSampleRate", requested_rate))


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
        score = 0 if default_rate == 16000 else abs(default_rate - 16000)
        matches.append((score, index, name))

    if not matches:
        raise RuntimeError(f"Microfone nao encontrado pelo nome: {device_name}")

    matches.sort()
    return matches[0][1]


def open_stream(pa: pyaudio.PyAudio, device_index: int | None, sample_rate: int):
    return pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=sample_rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=4000,
    )


def rms_level(data: bytes) -> int:
    samples = array("h")
    samples.frombytes(data)
    if not samples:
        return 0
    total = sum(sample * sample for sample in samples)
    return int((total / len(samples)) ** 0.5)


def test_microphone(stream, seconds: float, sample_rate: int) -> None:
    frames = max(1, int(seconds * sample_rate / 4000))
    print(f"Testando microfone por {seconds:g}s...")
    for _ in range(frames):
        data = stream.read(4000, exception_on_overflow=False)
        level = rms_level(data)
        bars = "#" * min(50, level // 200)
        print(f"nivel={level:5d} {bars}")


def append_output(output_path: Path, text: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as file:
        file.write(text + "\n")


def copy_to_clipboard(text: str) -> None:
    if not text.strip():
        return
    subprocess.run("clip", input=text, text=True, shell=True, check=False)


def main() -> int:
    args = build_parser().parse_args()
    SetLogLevel(-1)

    pa = pyaudio.PyAudio()
    stream = None
    try:
        if args.list_devices:
            list_input_devices(pa)
            return 0

        model_path = args.model.resolve()
        if not model_path.exists():
            print(f"Modelo nao encontrado: {model_path}", file=sys.stderr)
            return 2

        device_index = args.device
        if device_index is None:
            device_index = find_input_device(pa, args.device_name)

        sample_rate = resolve_rate(pa, device_index, args.rate)
        stream = open_stream(pa, device_index, sample_rate)
        stream.start_stream()

        device_name = (
            pa.get_device_info_by_index(device_index).get("name")
            if device_index is not None
            else pa.get_default_input_device_info().get("name")
        )
        print(f"Microfone: {device_name}")
        print(f"Taxa: {sample_rate} Hz")

        if args.test_seconds > 0:
            test_microphone(stream, args.test_seconds, sample_rate)
            return 0

        print("Carregando modelo...")
        model = Model(str(model_path))
        recognizer = KaldiRecognizer(model, sample_rate)

        session_header = f"\n--- Ditado {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---"
        append_output(args.output, session_header)
        print("Fale agora. Pressione Ctrl+C para finalizar.\n")

        final_parts: list[str] = []
        try:
            while True:
                data = stream.read(4000, exception_on_overflow=False)
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        final_parts.append(text)
                        append_output(args.output, text)
                        print(text)
                else:
                    partial = json.loads(recognizer.PartialResult()).get("partial", "").strip()
                    if partial:
                        print(f"\r{partial[:110]:110}", end="", flush=True)
        except KeyboardInterrupt:
            print("\nFinalizando...")

        result = json.loads(recognizer.FinalResult())
        text = result.get("text", "").strip()
        if text:
            final_parts.append(text)
            append_output(args.output, text)
            print(text)

        full_text = "\n".join(final_parts)
        if args.clipboard:
            copy_to_clipboard(full_text)
            print("Texto final copiado para a area de transferencia.")

        print(f"Salvo em: {args.output.resolve()}")
        return 0
    finally:
        if stream is not None:
            try:
                if stream.is_active():
                    stream.stop_stream()
                stream.close()
            except OSError:
                pass
        pa.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
