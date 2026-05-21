# Accuracy and speed optimisation

Local Ditado already applies, by default, the main techniques that separate a
"hobby" dictation tool from a competitive one. This guide explains what is enabled
and how to tune it.

## Already implemented

| Technique | Where | Effect |
| --- | --- | --- |
| Automatic `large-v3-turbo` model | `hardware.py` | "large" accuracy near "base" speed |
| Hardware fallback (turbo→small→base) | `hardware.choose_model` | good performance even on small GPU/CPU |
| `BatchedInferencePipeline` | `transcribe.py` | much higher transcription throughput |
| In-memory audio (no WAV on disk) | `audio.py` / `service.py` | removes I/O latency |
| Neural endpointing (Silero VAD) | `vad.py` | detects end of speech better than RMS; trims silence |
| `hotwords` + dictionary | `transcribe.py` / `postprocess.py` | gets names, acronyms, and jargon right |
| Pre-processing (normalisation, optional denoise) | `transcribe.preprocess_audio` | robustness in noise |
| Post-processing (punctuation, capitalisation) | `postprocess.py` | ready-to-use text |

## What matters most for ACCURACY

1. Good microphone close to your mouth; low background noise.
2. Larger model (`large-v3-turbo` or `medium`).
3. `hotwords`/dictionary with your frequent terms.
4. Context prompt (`prompts/pt-br-default.txt`).
5. `beam_size` 5.

## What matters most for SPEED

1. GPU/CUDA active (`local-ditado doctor` confirms).
2. Smaller model + batching.
3. Lower `silence_seconds` (stops sooner).
4. `beam_size` 1.

## Quick tuning

- More accurate: `precisao` profile (turbo, beam 5, denoise).
- Balanced: `equilibrado` profile (automatic model).
- Faster: `rapido` profile (base, beam 1, silence 0.8 s).

All of this is editable via the app (Settings) or the JSON files in `profiles/`.

## Next step (future phase): real-time streaming

The sidecar WebSocket API is already ready to stream **partial results** while you speak.
The implementation will transcribe in sliding windows and update the text incrementally,
matching the "real-time" feel of paid competitors.
