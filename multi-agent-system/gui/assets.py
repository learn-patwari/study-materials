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


def animation_frame_paths(state_name: str) -> list[str]:
    """Every frame of a state's animation, in playback order.

    Looks in ``assets/mascot_frames/<state_name>/frame_*.png``. Returns an
    empty list if that state has no animation prepared — callers fall back to
    the single static pose in that case.
    """
    frame_dir = assets_root() / "mascot_frames" / state_name
    if not frame_dir.is_dir():
        return []
    return [str(p) for p in sorted(frame_dir.glob("frame_*.png"))]
