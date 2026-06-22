"""Local sidecar (FastAPI + WebSocket) controlled by the interface (Tauri app).

Binds to 127.0.0.1 on an ephemeral port and writes ``server.json`` (port + token) to
the config directory so the app can discover the address. Nothing is exposed outside
the machine.

Dictation service events (microphone level, result, errors) are broadcast over the
WebSocket ``/ws`` for the interface to display in real time.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import threading

# WebSocket must be importable at module scope: with ``from __future__ import
# annotations`` the ``ws: WebSocket`` hint becomes the string "WebSocket", which
# FastAPI resolves against this module's globals. If it is only imported locally
# inside ``create_app``, FastAPI cannot resolve it, treats ``ws`` as a required
# query parameter, and rejects every /ws handshake with HTTP 403.
# (This module is only imported when serving, so fastapi stays effectively lazy.)
from fastapi import WebSocket, WebSocketDisconnect

from . import config, diagnostics, history, paths
from .platform import autostart
from .service import DictationService

log = logging.getLogger("localditado.server")


class AppState:
    def __init__(self) -> None:
        self.settings = config.load_settings()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.clients: set = set()
        self.service: DictationService | None = None
        self.hotkey_listener = None
        self.lock = threading.Lock()

    def emit(self, event: str, payload: dict) -> None:
        """Called from service threads; forwards to the asyncio event loop."""
        if self.loop is None:
            return
        message = json.dumps({"event": event, "payload": payload})
        self.loop.call_soon_threadsafe(asyncio.create_task, self._broadcast(message))

    async def _broadcast(self, message: str) -> None:
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_text(message)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    def ensure_service(self) -> DictationService:
        with self.lock:
            if self.service is None:
                self.service = DictationService(self.settings, on_event=self.emit)
                self._start_hotkey()
            return self.service

    def reload_service(self) -> None:
        with self.lock:
            self.settings = config.load_settings()
            self.service = DictationService(self.settings, on_event=self.emit)
            self._start_hotkey()

    def _start_hotkey(self) -> None:
        """(Re)register the global hotkey pointing to the current service."""
        from .platform.hotkey import HotkeyListener

        if self.hotkey_listener is not None:
            try:
                self.hotkey_listener.stop()
            except Exception:  # noqa: BLE001
                pass
        hotkey = str(self.settings.get("hotkey", "ctrl+alt+d"))

        def trigger() -> None:
            if self.service:
                self.service.toggle()

        try:
            self.hotkey_listener = HotkeyListener(hotkey, trigger)
            self.hotkey_listener.start()
        except Exception:  # noqa: BLE001
            log.exception("Could not register global hotkey %s", hotkey)
            self.hotkey_listener = None


def create_app(state: AppState):
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="Local Ditado", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # apenas loopback; o token protege as rotas
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _startup() -> None:
        state.loop = asyncio.get_running_loop()
        # Load the model in the background so server startup is not blocked.
        threading.Thread(target=state.ensure_service, daemon=True).start()

    @app.get("/api/status")
    def status() -> dict:
        svc = state.service
        return {
            "ready": svc is not None,
            "recording": bool(svc and svc.is_recording),
            "engine": svc.engine.kind if svc else None,
            "model": svc.engine.model_name if svc else None,
            "profile": state.settings.get("active_profile"),
        }

    @app.get("/api/config")
    def get_config() -> dict:
        return config.load_settings()

    @app.post("/api/config")
    def post_config(patch: dict) -> dict:
        config.update_config(patch)
        # Reload the service only if something that affects the engine/capture changed.
        engine_keys = {
            "engine", "whisper_model", "whisper_device", "whisper_compute_type",
            "beam_size", "batched", "batch_size", "vad", "language", "denoise",
            "device", "device_name", "sample_rate", "active_profile", "hotwords",
        }
        if engine_keys & set(patch):
            threading.Thread(target=state.reload_service, daemon=True).start()
        else:
            state.settings = config.load_settings()
            if state.service:
                state.service.settings = state.settings
        return config.load_settings()

    @app.get("/api/profiles")
    def get_profiles() -> dict:
        return {"profiles": config.list_profiles(), "active": state.settings.get("active_profile")}

    @app.post("/api/profile/{name}")
    def set_profile(name: str) -> dict:
        config.update_config({"active_profile": name})
        threading.Thread(target=state.reload_service, daemon=True).start()
        return {"active": name}

    @app.get("/api/devices")
    def devices() -> dict:
        from dataclasses import asdict

        from . import audio

        return {"devices": [asdict(d) for d in audio.list_input_devices()]}

    @app.get("/api/history")
    def get_history(limit: int = 100) -> dict:
        return {"entries": history.read_history(limit)}

    @app.delete("/api/history")
    def delete_history() -> dict:
        history.clear_history()
        return {"ok": True}

    @app.get("/api/diagnostics")
    def get_diagnostics() -> dict:
        return diagnostics.build_report()

    @app.get("/api/autostart")
    def get_autostart() -> dict:
        return {"enabled": autostart.is_enabled()}

    @app.post("/api/autostart")
    def set_autostart(body: dict) -> dict:
        if body.get("enabled"):
            autostart.enable()
        else:
            autostart.disable()
        return {"enabled": autostart.is_enabled()}

    @app.post("/api/toggle")
    def toggle() -> dict:
        svc = state.ensure_service()
        svc.toggle()
        return {"recording": svc.is_recording}

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        state.clients.add(ws)
        try:
            while True:
                await ws.receive_text()  # keep the connection alive
        except WebSocketDisconnect:
            pass
        finally:
            state.clients.discard(ws)

    return app


def _write_server_info(port: int, token: str) -> None:
    info = {"host": "127.0.0.1", "port": port, "token": token}
    (paths.config_dir() / "server.json").write_text(
        json.dumps(info, indent=2), encoding="utf-8"
    )


def run(host: str = "127.0.0.1", port: int = 0) -> None:
    import socket

    import uvicorn

    if port == 0:
        sock = socket.socket()
        sock.bind((host, 0))
        port = sock.getsockname()[1]
        sock.close()

    token = secrets.token_urlsafe(16)
    _write_server_info(port, token)
    log.info("Sidecar em http://%s:%d", host, port)
    print(json.dumps({"host": host, "port": port, "token": token}), flush=True)

    state = AppState()
    app = create_app(state)
    uvicorn.run(app, host=host, port=port, log_level="warning")
