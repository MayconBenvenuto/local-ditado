"""Compatibility shim: the service has moved to the ``localditado`` package in ``engine/``.

Keeps ``python dictado_hotkey.py`` working by delegating to the new cross-platform CLI
(``local-ditado service``).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "engine"))

from localditado.cli import main  # noqa: E402

if __name__ == "__main__":
    print("[warning] dictado_hotkey.py is a legacy shim. Use: local-ditado service")
    raise SystemExit(main(["service"]))
