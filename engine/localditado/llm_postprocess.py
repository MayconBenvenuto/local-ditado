"""Optional offline LLM cleanup of transcribed text ("smart formatting").

Whisper output is already good, but a tiny **local** language model can fix
punctuation, accents, and casing of proper nouns, and turn spoken structure into
clean text — without any of it leaving the machine. Off by default; enabled with
``llm_format: true`` plus a GGUF model at ``llm_model_path``. Runs via
llama-cpp-python (the heavy import stays inside the function).

Privacy is preserved: the model is local and nothing is sent over the network,
in line with the project's privacy principle.
"""

from __future__ import annotations

import logging

log = logging.getLogger("localditado.llm")

DEFAULT_INSTRUCTION = (
    "Você corrige texto ditado por voz. Conserte pontuação, acentuação e "
    "capitalização. NÃO altere as palavras, NÃO traduza, NÃO adicione comentários "
    "ou explicações. Responda apenas com o texto corrigido."
)

# Loaded models are cached by configuration so we pay the load cost only once.
_model_cache: dict[str, object] = {}


def _load_model(model_path: str, n_ctx: int, n_gpu_layers: int) -> object:
    key = f"{model_path}|{n_ctx}|{n_gpu_layers}"
    cached = _model_cache.get(key)
    if cached is not None:
        return cached
    from llama_cpp import Llama  # lazy, heavy optional dependency

    log.info("Loading local LLM for formatting: %s", model_path)
    llm = Llama(
        model_path=model_path,
        n_ctx=n_ctx,
        n_gpu_layers=n_gpu_layers,
        verbose=False,
    )
    _model_cache[key] = llm
    return llm


def format_text(text: str, settings: dict) -> str:
    """Return a cleaned-up version of ``text`` using a local LLM, or ``text``
    unchanged when disabled, misconfigured, or on any failure.
    """
    if not text or not settings.get("llm_format"):
        return text

    model_path = str(settings.get("llm_model_path", "") or "")
    if not model_path:
        log.warning("llm_format is on but llm_model_path is empty; skipping.")
        return text

    try:
        llm = _load_model(
            model_path,
            int(settings.get("llm_n_ctx", 2048)),
            int(settings.get("llm_gpu_layers", -1)),
        )
        instruction = str(settings.get("llm_format_instruction") or DEFAULT_INSTRUCTION)
        response = llm.create_chat_completion(  # type: ignore[attr-defined]
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            max_tokens=int(settings.get("llm_max_tokens", 512)),
        )
        output = str(response["choices"][0]["message"]["content"]).strip()
        return output or text
    except Exception:  # noqa: BLE001
        log.warning("LLM formatting failed; using the raw transcript.", exc_info=True)
        return text
