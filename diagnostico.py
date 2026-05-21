"""Compatibility shim: diagnostics have moved to ``localditado`` in ``engine/``.

``python diagnostico.py [--json]`` delegates to ``local-ditado doctor``.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "engine"))

from localditado.cli import main  # noqa: E402

if __name__ == "__main__":
    forward = ["doctor"]
    if "--json" in sys.argv[1:]:
        forward.append("--json")
    if "--devices-only" in sys.argv[1:]:
        forward = ["devices"]
    raise SystemExit(main(forward))
