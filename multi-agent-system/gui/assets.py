"""Locating bundled asset files.

Paths resolve against the project directory, never the current working
directory, so the app finds its artwork no matter where it was launched from.
When PyInstaller freezes the app it unpacks the bundle to a temporary folder
and points ``sys._MEIPASS`` at it, which is checked first.
"""
from __future__ import annotations

import sys
from pathlib import Path

# gui/assets.py -> project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def assets_root() -> Path:
    """The assets/ directory, frozen or not."""
    bundle_dir = getattr(sys, "_MEIPASS", None)
    base = Path(bundle_dir) if bundle_dir else _PROJECT_ROOT
    return base / "assets"


def asset_path(*parts: str) -> str:
    """Absolute path to an asset, e.g. ``asset_path("mascot", "idle.png")``."""
    return str(assets_root().joinpath(*parts))


def asset_exists(*parts: str) -> bool:
    return assets_root().joinpath(*parts).exists()
