"""Turn the raw mascot artwork into frames the app can load directly.

The raw PNGs ship with their own filename burned into the picture as a caption
(along the bottom, and along the top of the celebrating pose). They also come in
wildly different shapes — 216x400 for the idle pose, 409x337 for explaining — so
dropping them straight into the widget would show the caption text and make the
character jump and resize every time the pose changes.

This script fixes both, once, ahead of time:

    python tools/prepare_assets.py

Reads   assets/raw/*.png
Writes  assets/mascot/*.png   normalized animation frames
        assets/icons/*        tray / taskbar / profile art plus a multi-size .ico

The output is committed, so the app itself never needs Pillow. Re-run this after
editing or replacing anything in assets/raw/.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "assets" / "raw"
MASCOT_DIR = ROOT / "assets" / "mascot"
ICON_DIR = ROOT / "assets" / "icons"

# ── Tuning ────────────────────────────────────────────────────────────────────

# The canvas every pose is fitted into. Poses are scaled to fit and anchored
# bottom-centre, so the character's feet stay planted while the pose changes.
CANVAS_W = 240
CANVAS_H = 260

# A pixel counts as ink above this alpha. Below it is background or soft edge.
ALPHA_FLOOR = 32

# A row with fewer ink pixels than this is treated as blank. Tolerates the stray
# speck left behind by anti-aliasing.
def _blank_row_limit(width: int) -> int:
    return max(2, int(width * 0.002))

# Rows separated by a gap thinner than this fraction of the image belong to the
# same shape — it stops a soft horizontal seam from splitting the character in
# two. The caption always sits further away than this.
MERGE_GAP_FRAC = 0.02

# What makes a band a caption rather than part of the character. All three must
# hold. The character legitimately breaks into several bands (torso, legs,
# shoes) and the caption carries more ink than the shoes do, so ink alone can't
# tell them apart — but a line of text is uniquely thin, wide and pinned to an
# edge. In this art every caption scores >= 15 on aspect and no part of the
# character sits in the edge zones at all, so there is plenty of margin.
CAPTION_EDGE_FRAC = 0.10      # must sit entirely within the top/bottom 10%
CAPTION_MAX_HEIGHT_FRAC = 0.06  # ...and be no taller than 6% of the image
CAPTION_MIN_ASPECT = 6.0      # ...and be at least 6x wider than it is tall

# Sizes baked into the Windows .exe icon.
ICO_SIZES = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]

# raw filename -> output frame name
MASCOT_MAP = {
    "MASCOT_IDLE_STANDING.png": "idle.png",
    "MASCOT_WAVE_GREETING.png": "greeting.png",
    "MASCOT_THINKING_REASONING.png": "thinking.png",
    "MASCOT_WORKING_EXECUTING.png": "working.png",
    "MASCOT_EXPLAINING_RESPONSE.png": "explaining.png",
    "MASCOT_IDEA_SUGGESTION.png": "idea.png",
    "MASCOT_HAPPY_SUCCESS.png": "success.png",
    "MASCOT_CELEBRATING_COMPLETE.png": "celebrating.png",
    "MASCOT_CONFIDENT_READY.png": "ready.png",
}

# raw filename -> output icon name
ICON_MAP = {
    "LOGO_WINDOWS_TASKBAR.png": "taskbar.png",
    "LOGO_SYSTEM_TRAY.png": "tray.png",
    "LOGO_CHATBOT_PROFILE.png": "profile.png",
}

ICO_SOURCE = "LOGO_APPLICATION_EXE.png"


# ── Caption removal ───────────────────────────────────────────────────────────

def row_ink(image: Image.Image) -> list[int]:
    """Ink pixels per row, top to bottom."""
    alpha = image.getchannel("A")
    w, h = image.size
    data = alpha.tobytes()
    return [
        sum(1 for x in range(w) if data[y * w + x] >= ALPHA_FLOOR)
        for y in range(h)
    ]


def find_content_bands(counts: list[int], width: int, height: int) -> list[tuple[int, int, int]]:
    """Group rows into (top, bottom, mass) bands separated by blank space.

    Bands closer together than MERGE_GAP_FRAC are joined, so one shape with a
    faint seam through it stays one band.
    """
    limit = _blank_row_limit(width)
    bands: list[list[int]] = []
    run_start: int | None = None

    for y, count in enumerate(counts):
        if count > limit:
            if run_start is None:
                run_start = y
        elif run_start is not None:
            bands.append([run_start, y - 1, sum(counts[run_start:y])])
            run_start = None
    if run_start is not None:
        bands.append([run_start, len(counts) - 1, sum(counts[run_start:])])

    if not bands:
        return []

    merge_gap = max(1, int(height * MERGE_GAP_FRAC))
    merged = [bands[0]]
    for top, bottom, mass in bands[1:]:
        if top - merged[-1][1] <= merge_gap:
            merged[-1][1] = bottom
            merged[-1][2] += mass
        else:
            merged.append([top, bottom, mass])

    return [tuple(b) for b in merged]


def band_width(image: Image.Image, top: int, bottom: int) -> int:
    """Horizontal extent of the ink between two rows."""
    strip = image.crop((0, top, image.width, bottom + 1))
    bbox = strip.getchannel("A").point(lambda a: 255 if a >= ALPHA_FLOOR else 0).getbbox()
    return bbox[2] - bbox[0] if bbox else 0


def is_caption_band(image: Image.Image, top: int, bottom: int) -> bool:
    """A thin, wide strip pinned to the top or bottom edge is burned-in text."""
    height = image.height
    band_h = bottom - top + 1

    at_edge = bottom < height * CAPTION_EDGE_FRAC or top > height * (1 - CAPTION_EDGE_FRAC)
    thin = band_h <= height * CAPTION_MAX_HEIGHT_FRAC
    wide = band_width(image, top, bottom) / band_h >= CAPTION_MIN_ASPECT

    return at_edge and thin and wide


def strip_caption(image: Image.Image) -> Image.Image:
    """Drop the burned-in filename caption, keeping every part of the figure.

    The character routinely splits into several bands with clear space between
    them — torso, legs, shoes — so all non-caption bands are kept and the crop
    spans their full range.
    """
    bands = find_content_bands(row_ink(image), image.width, image.height)
    kept = [b for b in bands if not is_caption_band(image, b[0], b[1])]
    if not kept or len(kept) == len(bands):
        return image
    return image.crop((0, kept[0][0], image.width, kept[-1][1] + 1))


# ── Normalization ─────────────────────────────────────────────────────────────

def trim_alpha(image: Image.Image) -> Image.Image:
    bbox = image.getchannel("A").point(lambda a: 255 if a >= ALPHA_FLOOR else 0).getbbox()
    return image.crop(bbox) if bbox else image


def fit_to_canvas(image: Image.Image, width: int, height: int) -> Image.Image:
    """Scale to fit and place bottom-centre on a transparent canvas."""
    scale = min(width / image.width, height / image.height)
    new_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    resized = image.resize(new_size, Image.LANCZOS)

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.paste(resized, ((width - new_size[0]) // 2, height - new_size[1]), resized)
    return canvas


def square_pad(image: Image.Image) -> Image.Image:
    side = max(image.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(image, ((side - image.width) // 2, (side - image.height) // 2), image)
    return canvas


# ── Pipeline ──────────────────────────────────────────────────────────────────

def load_raw(name: str) -> Image.Image:
    path = RAW_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"missing raw asset: {path}")
    return Image.open(path).convert("RGBA")


def build_mascot_frames() -> int:
    MASCOT_DIR.mkdir(parents=True, exist_ok=True)
    for raw_name, out_name in MASCOT_MAP.items():
        image = load_raw(raw_name)
        before = image.size
        frame = fit_to_canvas(trim_alpha(strip_caption(image)), CANVAS_W, CANVAS_H)
        frame.save(MASCOT_DIR / out_name)
        print(f"  {raw_name:32} {before[0]}x{before[1]:<4} -> mascot/{out_name}")
    return len(MASCOT_MAP)


def build_icons() -> int:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    for raw_name, out_name in ICON_MAP.items():
        icon = square_pad(trim_alpha(load_raw(raw_name)))
        icon.resize((256, 256), Image.LANCZOS).save(ICON_DIR / out_name)
        print(f"  {raw_name:32} -> icons/{out_name}")

    ico = square_pad(trim_alpha(load_raw(ICO_SOURCE)))
    ico.resize((256, 256), Image.LANCZOS).save(ICON_DIR / "pattu.ico", sizes=ICO_SIZES)
    print(f"  {ICO_SOURCE:32} -> icons/pattu.ico ({len(ICO_SIZES)} sizes)")
    return len(ICON_MAP) + 1


def main() -> int:
    if not RAW_DIR.exists():
        print(f"error: {RAW_DIR} not found", file=sys.stderr)
        return 1

    print(f"Preparing assets from {RAW_DIR}\n")
    frames = build_mascot_frames()
    icons = build_icons()
    print(f"\nDone — {frames} mascot frames at {CANVAS_W}x{CANVAS_H}, {icons} icons.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
