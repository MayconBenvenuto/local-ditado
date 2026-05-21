"""Platform layer: isolates everything that is OS-specific.

Callers use ``paste``, ``hotkey``, ``sound``, and ``autostart`` without needing to
know whether they are on Windows, Linux, or macOS.
"""
