# Voice Commands

When `voice_commands` is enabled (default), you can dictate punctuation and line breaks
by speaking these words. They are recognised with or without accents and case-insensitively.

| Say | Result |
| --- | --- |
| comma | `,` |
| period / full stop | `.` |
| semicolon | `;` |
| colon | `:` |
| question mark | `?` |
| exclamation mark | `!` |
| ellipsis | `...` |
| open parenthesis | `(` |
| close parenthesis | `)` |
| dash / em dash | `—` |
| new line | line break |
| new paragraph | blank line (paragraph) |

Punctuation is attached to the preceding word and spacing is adjusted automatically.

## Example

> You say: *"hello comma how are you period new line goodbye"*

Result:

```text
Hello, how are you.
Goodbye
```

## Disable

Set `voice_commands: false` in `config.json` (or uncheck it in the app's Settings tab)
if you prefer to transcribe the words literally.

## Adding / changing commands (for developers)

The list lives in `VOICE_COMMANDS` in `engine/localditado/postprocess.py`. Place longer
phrases before shorter ones (e.g. "question mark" before "question") and add a test in
`engine/tests/test_postprocess.py`. See the rules in [../AGENTS.md](../AGENTS.md).
