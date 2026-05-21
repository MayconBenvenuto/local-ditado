# Security

Local Ditado records audio from the microphone and pastes text into the focused application.
This requires care.

## Sensitive data

- Do not publish files from `recordings/`.
- Do not publish `ditado.txt` or any local transcript file.
- Do not publish logs if they contain sensitive text.

## Reporting vulnerabilities

Open an issue with enough detail to reproduce the problem, but without exposing private data.
For sensitive issues, describe the impact and arrange a private channel with the maintainers.

## Current security model

- Speech recognition runs entirely locally.
- The service listens on `127.0.0.1` only (loopback — not reachable from the network).
- Text is written to the clipboard and pasted into the focused window.
- Models downloaded from third parties should be treated as external dependencies.
