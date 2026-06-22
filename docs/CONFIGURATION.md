# Configuration

Options come from four sources, weakest to strongest:

```text
DEFAULT_SETTINGS  <  profiles/<profile>.json  <  config.json (user)  <  CLI flags
```

- **`config.json`** lives in the OS config directory (see its path in `local-ditado doctor`),
  **not** in the repository. It can be edited via the app, the tray, or manually.
- **Profiles** live in `profiles/` and define only the precision/speed subset.

## All options reference

### Microphone

| Key | Default | Description |
| --- | --- | --- |
| `device` | `null` | Microphone index (`null` = OS default). See `local-ditado devices`. |
| `device_name` | `null` | Substring of the microphone name (alternative to index). |
| `sample_rate` | `16000` | Capture sample rate (Hz). Whisper expects 16 kHz. |

### Transcription engine

| Key | Default | Description |
| --- | --- | --- |
| `engine` | `"whisper"` | `whisper` (primary), `parakeet` (NVIDIA NeMo, `parakeet` extra) or `vosk` (offline fallback). A missing backend degrades gracefully (→ whisper → vosk). |
| `parakeet_model` | `"nvidia/parakeet-tdt-0.6b-v3"` | Model used when `engine` = `parakeet`. Multilingual, very fast on CUDA. |
| `language` | `"pt"` | Language code (`pt`, `en`, `es`…) or `auto` to detect. |
| `whisper_model` | `"auto"` | `auto` chooses by hardware; or `large-v3-turbo`, `medium`, `small`, `base`, `tiny`. |
| `whisper_device` | `"auto"` | `auto`, `cpu`, or `cuda`. |
| `whisper_compute_type` | `"auto"` | `auto` chooses by device (`int8_float16` GPU, `int8` CPU). |
| `beam_size` | `5` | Higher = more accurate; `1` = fastest. |
| `cpu_threads` | `0` | `0` = automatic (machine cores). |
| `batched` | `true` | Use `BatchedInferencePipeline` (faster). |
| `batch_size` | `8` | Batch size when `batched`. |
| `warmup` | `true` | Run a silent inference at load so the **first** dictation is fast (avoids the cuDNN/CT2 autotune spike). |

> The `auto` resolution logic lives in `localditado/hardware.py`: ample GPU →
> `large-v3-turbo`; small GPU → `small`/`base`; CPU → `small`/`base` by core count.

### Capture and endpointing

| Key | Default | Description |
| --- | --- | --- |
| `vad` | `"silero"` | `silero` (neural, recommended) or `rms` (energy, fallback). |
| `silence_seconds` | `1.5` | Silence (s) before auto-stopping after speech is detected. |
| `speech_rms_threshold` | `450` | Energy threshold for `rms` mode. |
| `max_seconds` | `120` | Safety cap: maximum recording duration. |
| `denoise` | `false` | Noise reduction before transcribing (requires `denoise` extra). |
| `denoise_method` | `"spectral"` | `spectral` (noisereduce) or `deepfilternet` (neural, stronger; `deepfilter` extra). |

### Post-processing

| Key | Default | Description |
| --- | --- | --- |
| `initial_prompt_file` | `prompts/pt-br-default.txt` | Context prompt to bias style/terms. |
| `hotwords` | `""` | Terms to bias transcription (names, acronyms, jargon). |
| `voice_commands` | `true` | Interpret "comma", "new line", etc. See [VOICE_COMMANDS.md](VOICE_COMMANDS.md). |
| `capitalize` | `true` | Capitalise the start of sentences. |
| `dictionary` | `{}` | Literal substitutions `{ "heard": "corrected" }` (case-insensitive, whole word). |
| `llm_format` | `false` | Clean up the transcript with a **local** LLM (offline; requires `llm` extra). |
| `llm_model_path` | `""` | Path to a local GGUF model (llama-cpp-python) used when `llm_format` is on. |
| `llm_gpu_layers` | `-1` | Layers to offload to GPU (`-1` = all when possible). |
| `llm_format_instruction` | `""` | Override the default cleanup instruction sent to the LLM. |

> `llm_format` runs entirely on-device — nothing is sent over the network, in
> keeping with the privacy principle. It only activates when a model path is set.

### Output and privacy

| Key | Default | Description |
| --- | --- | --- |
| `auto_paste` | `true` | Paste the text into the focused app. |
| `save_transcript` | `true` | Append to history (`history.jsonl`). |
| `save_recordings` | `false` | Save the WAV of each dictation (off for privacy). |
| `recordings_retention_days` | `7` | Delete recordings older than this (`0` = never delete). |

### System

| Key | Default | Description |
| --- | --- | --- |
| `active_profile` | `"equilibrado"` | Active profile (`precisao`, `equilibrado`, `rapido`). |
| `hotkey` | `"ctrl+alt+d"` | Global hotkey. E.g. `ctrl+shift+space`, `alt+f2`. |
| `feedback_sound` | `true` | Start/stop/error beeps. |
| `vosk_model` | (data dir) | Path to the Vosk model (fallback). |
| `task_name` | `"LocalDitado"` | Name used in legacy autostart integrations. |

## Example `config.json`

```json
{
  "active_profile": "equilibrado",
  "device_name": "Yeti",
  "language": "pt",
  "whisper_model": "auto",
  "hotkey": "ctrl+alt+d",
  "voice_commands": true,
  "dictionary": { "cubernetes": "Kubernetes", "maicon": "Maycon" },
  "hotwords": "Kubernetes, faster-whisper, CTranslate2",
  "save_recordings": false
}
```

## Profile format (`profiles/precisao.json`)

```json
{
  "whisper_model": "large-v3-turbo",
  "whisper_device": "auto",
  "whisper_compute_type": "auto",
  "beam_size": 5,
  "batched": true,
  "batch_size": 8,
  "vad": "silero",
  "silence_seconds": 2.0,
  "denoise": true,
  "cpu_threads": 0
}
```
