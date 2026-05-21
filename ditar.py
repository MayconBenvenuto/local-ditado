"""Compatibility shim: manual dictation has moved to ``localditado`` in ``engine/``.

``python ditar.py`` now delegates to the cross-platform CLI. Examples:
    python ditar.py            -> equivalent to 'local-ditado once'
    python ditar.py --list-devices (legacy) -> use 'local-ditado devices'
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "engine"))

from localditado.cli import main  # noqa: E402

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--list-devices" in args:
        raise SystemExit(main(["devices"]))
    print("[warning] ditar.py is a legacy shim. Use: local-ditado once")
    raise SystemExit(main(["once"]))
