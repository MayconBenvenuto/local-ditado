"""Enables ``python -m localditado`` and serves as the PyInstaller binary entry point."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
