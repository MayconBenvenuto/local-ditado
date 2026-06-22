"""Streaming stabiliser for real-time partial transcripts (LocalAgreement-2).

Whisper is not a streaming model: to show text *while* the user speaks, we
re-transcribe a growing audio buffer every few hundred milliseconds. Each pass
can revise the tail, which would make the on-screen text flicker.

``LocalAgreement`` solves this: it only **commits** (emits as final) the prefix
that two consecutive passes agree on. Confirmed text never changes; the unstable
tail is returned separately as a live preview the UI can show greyed-out.

This module is pure logic (no audio, no model) so it is fully unit-tested. The
real-time loop that feeds it lives in the service layer.
"""

from __future__ import annotations

import re

_TOKEN_SPLIT = re.compile(r"\s+")


def tokenize(text: str) -> list[str]:
    """Whitespace tokenisation good enough for word-level agreement."""
    text = text.strip()
    return _TOKEN_SPLIT.split(text) if text else []


class LocalAgreement:
    """LocalAgreement-2 incremental stabiliser over word tokens."""

    def __init__(self) -> None:
        self.committed: list[str] = []
        self._prev: list[str] = []

    def update(self, text: str) -> tuple[str, str]:
        """Feed the latest full hypothesis for the current audio buffer.

        Returns ``(newly_committed, preview)`` where ``newly_committed`` is the
        text that just became final (append it to the output) and ``preview`` is
        the still-unstable tail (show it, but expect it to change).
        """
        tokens = tokenize(text)

        agreed = 0
        for current, previous in zip(tokens, self._prev, strict=False):
            if current == previous:
                agreed += 1
            else:
                break

        newly: list[str] = []
        if agreed > len(self.committed):
            newly = tokens[len(self.committed) : agreed]
            self.committed = tokens[:agreed]

        self._prev = tokens
        preview = tokens[len(self.committed) :]
        return " ".join(newly), " ".join(preview)

    def finalize(self, text: str | None = None) -> str:
        """End of speech: commit everything that is left (no more revisions)."""
        tokens = tokenize(text) if text is not None else list(self._prev)
        if len(tokens) < len(self.committed):
            tokens = self.committed  # never drop already-confirmed words
        newly = tokens[len(self.committed) :]
        self.committed = tokens
        self._prev = tokens
        return " ".join(newly)

    @property
    def text(self) -> str:
        """All committed text so far."""
        return " ".join(self.committed)

    def reset(self) -> None:
        self.committed = []
        self._prev = []
