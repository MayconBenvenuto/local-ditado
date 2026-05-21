"""Post-processing for transcribed text.

Three layers, all configurable:
1. User **dictionary** — literal substitutions (fixes names/jargon).
2. **Voice commands** — dictate punctuation and breaks ("comma", "new line", ...).
3. **Capitalisation** and spacing adjustment around punctuation.
"""

from __future__ import annotations

import re

# Spoken phrase -> punctuation. Order matters: longer phrases first.
VOICE_COMMANDS: list[tuple[str, str]] = [
    (r"novo par[áa]grafo", "\n\n"),
    (r"nova linha", "\n"),
    (r"ponto e v[íi]rgula", ";"),
    (r"ponto de interroga[çc][ãa]o", "?"),
    (r"ponto de exclama[çc][ãa]o", "!"),
    (r"ponto final", "."),
    (r"reretic[êe]ncias|retic[êe]ncias", "..."),
    (r"dois pontos", ":"),
    (r"v[íi]rgula", ","),
    (r"interroga[çc][ãa]o", "?"),
    (r"exclama[çc][ãa]o", "!"),
    (r"abre par[êe]nteses", "("),
    (r"fecha par[êe]nteses", ")"),
    (r"travess[ãa]o", "—"),
    (r"\bponto\b", "."),
]

_PUNCT_AFTER = ".,;:!?)…"
_NO_SPACE_BEFORE = re.compile(r"\s+([.,;:!?)\]…])")
_NO_SPACE_AFTER_OPEN = re.compile(r"([(\[])\s+")
_MULTISPACE = re.compile(r"[ \t]{2,}")
_SPACE_NEWLINE = re.compile(r"[ \t]*\n[ \t]*")
_SENTENCE_SPLIT = re.compile(r"([.!?]\s+|\n+)")


def apply_dictionary(text: str, mapping: dict[str, str]) -> str:
    for wrong, right in mapping.items():
        if not wrong:
            continue
        text = re.sub(rf"\b{re.escape(wrong)}\b", right, text, flags=re.IGNORECASE)
    return text


def apply_voice_commands(text: str) -> str:
    for phrase, repl in VOICE_COMMANDS:
        # Consume the preceding space to attach punctuation to the word on the left.
        text = re.sub(rf"\s*\b(?:{phrase})\b", repl, text, flags=re.IGNORECASE)
    return text


def fix_spacing(text: str) -> str:
    text = _NO_SPACE_BEFORE.sub(r"\1", text)
    text = _NO_SPACE_AFTER_OPEN.sub(r"\1", text)
    text = _MULTISPACE.sub(" ", text)
    text = _SPACE_NEWLINE.sub("\n", text)
    # Ensure a space after punctuation when it is attached to another word.
    text = re.sub(rf"([{re.escape(_PUNCT_AFTER)}])(?=[A-Za-zÀ-ÿ])", r"\1 ", text)
    return text.strip()


def capitalize_sentences(text: str) -> str:
    parts = _SENTENCE_SPLIT.split(text)
    out: list[str] = []
    capitalize_next = True
    for part in parts:
        if not part:
            continue
        if _SENTENCE_SPLIT.fullmatch(part):
            out.append(part)
            capitalize_next = True
            continue
        if capitalize_next:
            stripped = part.lstrip()
            lead = part[: len(part) - len(stripped)]
            part = lead + (stripped[:1].upper() + stripped[1:] if stripped else stripped)
            capitalize_next = False
        out.append(part)
    return "".join(out)


def process(
    text: str,
    *,
    dictionary: dict[str, str] | None = None,
    voice_commands: bool = True,
    capitalize: bool = True,
) -> str:
    if not text:
        return text
    if dictionary:
        text = apply_dictionary(text, dictionary)
    if voice_commands:
        text = apply_voice_commands(text)
    text = fix_spacing(text)
    if capitalize:
        text = capitalize_sentences(text)
    return text


def process_with_settings(text: str, settings: dict) -> str:
    return process(
        text,
        dictionary=settings.get("dictionary") or {},
        voice_commands=bool(settings.get("voice_commands", True)),
        capitalize=bool(settings.get("capitalize", True)),
    )
