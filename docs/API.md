# Sidecar API (HTTP + WebSocket)

The `local-ditado serve` command starts a **local** server (FastAPI) that the interface
uses to control the engine and receive real-time events. It is the boundary between the
Tauri app and Python.

## Address and discovery

- Binds to `127.0.0.1` (loopback only — **not** reachable from the network) on an **ephemeral port**.
- On startup, prints a JSON line to stdout and writes `server.json` to the config directory:

```json
{ "host": "127.0.0.1", "port": 53120, "token": "xxxxxxxx" }
```

The Tauri shell reads that stdout line and exposes it to the frontend via the `get_server` command.
During frontend development, open the page with `?api=http://127.0.0.1:<port>`.

> The `token` is generated for future authentication use; today the loopback is the protection.

## REST endpoints

| Method | Route | Body | Response / effect |
| --- | --- | --- | --- |
| GET | `/api/status` | — | `{ ready, recording, engine, model, profile }` |
| GET | `/api/config` | — | effective settings (full merge) |
| POST | `/api/config` | partial JSON patch | saves and reloads the engine if needed; returns settings |
| GET | `/api/profiles` | — | `{ profiles: [...], active }` |
| POST | `/api/profile/{name}` | — | switches the active profile and reloads |
| GET | `/api/devices` | — | `{ devices: [{ index, name, channels, default_sample_rate }] }` |
| GET | `/api/history?limit=100` | — | `{ entries: [{ ts, text, engine, model, elapsed, language }] }` |
| DELETE | `/api/history` | — | clears the history |
| GET | `/api/diagnostics` | — | same report as `doctor` |
| GET | `/api/autostart` | — | `{ enabled }` |
| POST | `/api/autostart` | `{ "enabled": true }` | enable/disable start on login |
| POST | `/api/toggle` | — | start/stop a dictation; returns `{ recording }` |

### Engine reload

`POST /api/config` reloads the engine (in background) only if the patch touches keys that
affect capture/transcription: `engine`, `whisper_model`, `whisper_device`,
`whisper_compute_type`, `beam_size`, `batched`, `batch_size`, `vad`, `language`, `denoise`,
`device`, `device_name`, `sample_rate`, `active_profile`, `hotwords`. Other changes apply
without reloading the model.

## WebSocket `/ws`

Connect to `ws://127.0.0.1:<port>/ws`. The server sends JSON messages in the format:

```json
{ "event": "<name>", "payload": { ... } }
```

| Event | Payload | When |
| --- | --- | --- |
| `ready` | `{ engine, model }` | engine loaded and ready |
| `recording_started` | `{}` | recording started |
| `level` | `{ level }` (0..1) | every audio block — feeds the level meter |
| `transcribing` | `{}` | recording stopped, transcribing |
| `result` | `{ text, elapsed, engine, model, audio_seconds }` or `{ text:"", empty:true }` | transcription done |
| `error` | `{ message }` | failure in the cycle |

> The WebSocket channel is already prepared to stream **partial results** (future feature):
> it will be enough to emit incremental events before the final `result`.

## Example (JavaScript)

```js
const base = "http://127.0.0.1:53120";
const ws = new WebSocket(base.replace("http", "ws") + "/ws");
ws.onmessage = (e) => {
  const { event, payload } = JSON.parse(e.data);
  if (event === "level") meter.style.width = payload.level * 100 + "%";
  if (event === "result") console.log(payload.text);
};
await fetch(base + "/api/toggle", { method: "POST" }); // start/stop dictation
```

## Security notes

- No restrictive CORS because everything is loopback; still, **do not** expose this port to the network.
- The server makes no external calls. Models are downloaded by `faster-whisper`/Hugging Face
  only on the first use of a new model.
