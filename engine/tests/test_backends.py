"""Tests for the pluggable backend registry and LLM post-processing guard.

These are pure-logic checks: no model is loaded, so they run without a GPU,
microphone, or the optional heavy dependencies.
"""

from __future__ import annotations

from localditado import llm_postprocess, transcribe


def test_registry_has_known_backends():
    assert set(transcribe.BACKEND_BUILDERS) >= {"whisper", "parakeet", "vosk"}
    assert all(callable(builder) for builder in transcribe.BACKEND_BUILDERS.values())


def test_llm_format_is_noop_when_disabled():
    assert llm_postprocess.format_text("texto", {"llm_format": False}) == "texto"
    assert llm_postprocess.format_text("", {"llm_format": True}) == ""


def test_llm_format_skips_when_no_model_path():
    # Enabled but misconfigured (empty path) → returns input unchanged, no crash.
    assert llm_postprocess.format_text("ola", {"llm_format": True, "llm_model_path": ""}) == "ola"
