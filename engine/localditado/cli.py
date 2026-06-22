"""Local Ditado command-line interface.

Subcommands:
  service   Resident service with global hotkey (main mode).
  once      Single dictation and exit (ideal for desktop shortcuts / Wayland).
  serve     Start the HTTP/WebSocket sidecar used by the desktop app.
  tray      System tray icon (requires the [app] extra).
  devices   List microphones.
  test      Test the microphone level for a few seconds.
  bench     Measure transcription speed (RTFx) without a microphone.
  doctor    Environment diagnostics (use --json for structured output).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
import time

from . import config, paths


def _setup_logging() -> None:
    logging.basicConfig(
        filename=str(paths.log_path()),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        encoding="utf-8",
    )


def _load(args: argparse.Namespace) -> dict:
    overrides = {
        "device": getattr(args, "device", None),
        "device_name": getattr(args, "device_name", None),
        "whisper_model": getattr(args, "model", None),
        "language": getattr(args, "language", None),
        "engine": getattr(args, "engine", None),
    }
    return config.load_settings(profile_name=getattr(args, "profile", None), overrides=overrides)


def _print_event(event: str, payload: dict) -> None:
    if event == "recording_started":
        print("🎙️  Recording... (speak; stop in silence or press the hotkey)")
    elif event == "transcribing":
        print("✍️  Transcribing...")
    elif event == "result":
        text = payload.get("text", "")
        if payload.get("empty"):
            print("(silence — nothing transcribed)")
        else:
            print(f"\n{text}\n")
            meta = f"{payload.get('audio_seconds', '?')}s audio → {payload.get('elapsed', '?')}s"
            print(f"   [{payload.get('engine')}/{payload.get('model')} · {meta}]")
    elif event == "error":
        print(f"❌ {payload.get('message')}", file=sys.stderr)
    elif event == "ready":
        print(f"✅ Engine ready: {payload.get('engine')}/{payload.get('model')}")


# --------------------------- subcommands ---------------------------
def cmd_service(args: argparse.Namespace) -> int:
    from .platform.hotkey import HotkeyListener
    from .service import DictationService

    settings = _load(args)
    print(f"Loading Local Ditado (profile: {settings.get('active_profile')})...")
    service = DictationService(settings, on_event=_print_event)

    hotkey = str(settings.get("hotkey", "ctrl+alt+d"))
    listener = HotkeyListener(hotkey, service.toggle)
    listener.start()
    print(f"Service active. Global hotkey: {hotkey}. Ctrl+C to quit.")
    try:
        listener.join()
    except KeyboardInterrupt:
        print("\nShutting down...")
        listener.stop()
    return 0


def cmd_once(args: argparse.Namespace) -> int:
    from .service import DictationService

    settings = _load(args)
    done = threading.Event()

    def on_event(event: str, payload: dict) -> None:
        _print_event(event, payload)
        if event in ("result", "error"):
            done.set()

    service = DictationService(settings, on_event=on_event)
    service.toggle()
    # Wait for the cycle to finish.
    while not done.is_set():
        time.sleep(0.1)
    time.sleep(0.2)
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from . import server

    server.run(port=args.port)
    return 0


def cmd_tray(args: argparse.Namespace) -> int:
    from . import tray

    return tray.main()


def cmd_devices(_args: argparse.Namespace) -> int:
    from . import audio

    for dev in audio.list_input_devices():
        print(f"{dev.index}: {dev.name} | channels={dev.channels} | {dev.default_sample_rate} Hz")
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    from . import audio

    settings = _load(args)
    device = audio.resolve_device_index(
        settings.get("device"), settings.get("device_name"), int(settings.get("sample_rate", 16000))
    )
    stop = threading.Event()
    threading.Timer(args.seconds, stop.set).start()
    print(f"Testing microphone for {args.seconds:g}s (speak to see the level)...")

    def on_level(level: float) -> None:
        bars = "#" * int(min(50, level * 50))
        print(f"\rlevel {level:4.2f} {bars:<50}", end="", flush=True)

    audio.record_until_stop(
        stop, device=device, sample_rate=int(settings.get("sample_rate", 16000)),
        silence_seconds=999, max_seconds=args.seconds, on_level=on_level,
    )
    print("\nOK.")
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    """Measure raw transcription throughput (RTFx) on this machine.

    Uses synthetic audio with the VAD filter **off** so the model actually
    processes the whole buffer — otherwise Whisper's VAD would skip the
    speechless test signal and report a meaningless speed.
    """
    import time

    import numpy as np

    from . import transcribe

    settings = _load(args)
    settings["warmup"] = False  # warm up explicitly below, excluded from timing
    sr = int(settings.get("sample_rate", 16000))
    seconds = float(args.seconds)

    # Synthetic broadband signal (no microphone needed). Content does not matter
    # for a throughput measurement; what matters is processing the full buffer.
    rng = np.random.default_rng(0)
    audio = (0.05 * rng.standard_normal(int(seconds * sr))).astype(np.float32)

    print(f"Loading engine (profile: {settings.get('active_profile')})...")
    engine = transcribe.Engine(settings)
    backend = engine.backend
    language = settings.get("language", "pt")
    print(f"Engine: {engine.kind}/{engine.model_name} — warming up...")
    backend.transcribe(audio[:sr], language=language, vad_filter=False)

    elapsed: list[float] = []
    for i in range(args.runs):
        started = time.perf_counter()
        backend.transcribe(audio, language=language, vad_filter=False)
        run = time.perf_counter() - started
        elapsed.append(run)
        print(f"  run {i + 1}/{args.runs}: {run:.2f}s")

    best = min(elapsed)
    avg = sum(elapsed) / len(elapsed)
    print(
        f"\n{seconds:g}s audio · best {best:.2f}s ({seconds / best:.1f}x realtime) · "
        f"avg {avg:.2f}s ({seconds / avg:.1f}x realtime)"
    )
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    from . import diagnostics

    report = diagnostics.build_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        diagnostics.print_report(report)
    return 0


# --------------------------- parser ---------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="local-ditado", description=__doc__)
    sub = parser.add_subparsers(dest="command")

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--profile", help="precisao, equilibrado, or rapido")
        p.add_argument("--device", type=int, help="microphone index")
        p.add_argument("--device-name", help="substring of the microphone name")
        p.add_argument("--model", help="Whisper model (or 'auto')")
        p.add_argument("--language", help="language code (e.g. pt, en, 'auto')")
        p.add_argument("--engine", choices=("whisper", "vosk"))

    p_service = sub.add_parser("service", help="resident service with global hotkey")
    add_common(p_service)
    p_service.set_defaults(func=cmd_service)

    p_once = sub.add_parser("once", help="single dictation and exit")
    add_common(p_once)
    p_once.set_defaults(func=cmd_once)

    p_serve = sub.add_parser("serve", help="HTTP/WebSocket sidecar for the app")
    p_serve.add_argument("--port", type=int, default=0, help="0 = ephemeral port")
    p_serve.set_defaults(func=cmd_serve)

    p_tray = sub.add_parser("tray", help="system tray icon")
    p_tray.set_defaults(func=cmd_tray)

    p_devices = sub.add_parser("devices", help="list microphones")
    p_devices.set_defaults(func=cmd_devices)

    p_test = sub.add_parser("test", help="test the microphone level")
    add_common(p_test)
    p_test.add_argument("--seconds", type=float, default=5.0)
    p_test.set_defaults(func=cmd_test)

    p_bench = sub.add_parser("bench", help="measure transcription speed (RTFx)")
    add_common(p_bench)
    p_bench.add_argument("--seconds", type=float, default=10.0, help="length of test audio")
    p_bench.add_argument("--runs", type=int, default=3, help="number of timed runs")
    p_bench.set_defaults(func=cmd_bench)

    p_doctor = sub.add_parser("doctor", help="environment diagnostics")
    p_doctor.add_argument("--json", action="store_true")
    p_doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    config.ensure_config()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        # No subcommand: run the resident service (friendly default behaviour).
        return cmd_service(parser.parse_args(["service"]))
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
