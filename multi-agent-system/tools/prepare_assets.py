"""Turn the raw mascot artwork into frames the app can load directly.

This reads the SprintForge asset pack layout:

    assets/raw/mascot/<state>.png        a poster pose per state
    assets/raw/animations/<state>.webp   a looping animation per state (WEBP,
                                          not GIF — GIF's 1-bit transparency
                                          leaves later frames opaque-black;
                                          WEBP carries real per-frame alpha)
    assets/raw/icons/*.png               tray / taskbar / profile / .exe art

and writes:

    assets/mascot/<state>.png            poster frame — used for the icon-ish
                                          single-frame lookups tests rely on
    assets/mascot_frames/<state>/*.png   the full animation, numbered in order
    assets/icons/*                       tray / taskbar / profile art plus a
                                          multi-size .ico

    python tools/prepare_assets.py

The output is committed, so the app itself never needs Pillow. Re-run this
after editing or replacing anything in assets/raw/.

Some art packs bake their filename into the picture as a caption (thin,
wide, pinned to an edge). ``strip_caption`` removes it when present and is a
no-op otherwise, so this still works unmodified on packs that are already
clean, like this one.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "assets" / "raw"
MASCOT_DIR = ROOT / "assets" / "mascot"
FRAMES_DIR = ROOT / "assets" / "mascot_frames"
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
# two.
MERGE_GAP_FRAC = 0.02

# What makes a band a caption rather than part of the character. All three must
# hold — see the module docstring.
CAPTION_EDGE_FRAC = 0.10
CAPTION_MAX_HEIGHT_FRAC = 0.06
CAPTION_MIN_ASPECT = 6.0

# Sizes baked into the Windows .exe icon.
ICO_SIZES = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]

# Every pose in the state machine, and its raw filenames.
STATES = [
    "idle",
    "greeting",
    "thinking",
    "working",
    "explaining",
    "idea",
    "success",
    "celebrating",
    "ready",
]

# raw filename -> output icon name
ICON_MAP = {
    "windows_taskbar.png": "taskbar.png",
    "system_tray.png": "tray.png",
    "chatbot_profile.png": "profile.png",
}

ICO_SOURCE = "application_exe.png"


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
    """Drop a burned-in filename caption if present, keeping the whole figure.

    A no-op when there's nothing caption-shaped to remove, so this is safe to
    run on art that never had one.
    """
    bands = find_content_bands(row_ink(image), image.width, image.height)
    kept = [b for b in bands if not is_caption_band(image, b[0], b[1])]
    if not kept or len(kept) == len(bands):
        return image
    return image.crop((0, kept[0][0], image.width, kept[-1][1] + 1))


# ── Normalization ─────────────────────────────────────────────────────────────

def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    return image.getchannel("A").point(lambda a: 255 if a >= ALPHA_FLOOR else 0).getbbox()


def trim_alpha(image: Image.Image) -> Image.Image:
    bbox = alpha_bbox(image)
    return image.crop(bbox) if bbox else image


def fit_to_canvas(image: Image.Image, width: int, height: int) -> Image.Image:
    """Scale to fit and place bottom-centre on a transparent canvas."""
    scale = min(width / image.width, height / image.height)
    new_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    resized = image.resize(new_size, Image.LANCZOS)

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.paste(resized, ((width - new_size[0]) // 2, height - new_size[1]), resized)
    return canvas


def fit_crop_to_canvas(
    image: Image.Image, crop: tuple[int, int, int, int], width: int, height: int
) -> Image.Image:
    """Like fit_to_canvas, but scaled to a pre-computed crop rather than the
    frame's own bbox — so every frame in a sequence uses the identical scale
    and placement and the character doesn't jitter as it animates."""
    cropped = image.crop(crop)
    return fit_to_canvas(cropped, width, height)


def square_pad(image: Image.Image) -> Image.Image:
    side = max(image.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(image, ((side - image.width) // 2, (side - image.height) // 2), image)
    return canvas


# ── Pipeline ──────────────────────────────────────────────────────────────────

def load_raw(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(f"missing raw asset: {path}")
    return Image.open(path).convert("RGBA")


def build_mascot_posters() -> int:
    """The single representative frame per state — assets/mascot/<state>.png."""
    MASCOT_DIR.mkdir(parents=True, exist_ok=True)
    for state in STATES:
        src = RAW_DIR / "mascot" / f"{state}.png"
        image = load_raw(src)
        before = image.size
        frame = fit_to_canvas(trim_alpha(strip_caption(image)), CANVAS_W, CANVAS_H)
        frame.save(MASCOT_DIR / f"{state}.png")
        print(f"  mascot/{state}.png      {before[0]}x{before[1]:<4} -> mascot/{state}.png")
    return len(STATES)


def build_mascot_sequences() -> int:
    """The full per-state animation — assets/mascot_frames/<state>/frame_NNN.png.

    Every frame in one state's loop is cropped and scaled identically (using
    the union of every frame's ink, not each frame's own bbox) so the
    character's feet stay planted through the whole animation instead of
    jittering as the pose subtly shifts frame to frame.
    """
    total = 0
    for state in STATES:
        anim_path = RAW_DIR / "animations" / f"{state}.webp"
        if not anim_path.exists():
            continue

        anim = Image.open(anim_path)
        frames = [f.convert("RGBA") for f in ImageSequence.Iterator(anim)]
        if not frames:
            continue

        union = None
        for frame in frames:
            bbox = alpha_bbox(frame)
            if bbox is None:
                continue
            union = bbox if union is None else (
                min(union[0], bbox[0]),
                min(union[1], bbox[1]),
                max(union[2], bbox[2]),
                max(union[3], bbox[3]),
            )
        if union is None:
            continue

        out_dir = FRAMES_DIR / state
        out_dir.mkdir(parents=True, exist_ok=True)
        for existing in out_dir.glob("frame_*.png"):
            existing.unlink()

        for i, frame in enumerate(frames):
            normalized = fit_crop_to_canvas(frame, union, CANVAS_W, CANVAS_H)
            normalized.save(out_dir / f"frame_{i:03d}.png")

        print(f"  animations/{state}.webp  {len(frames)} frames -> mascot_frames/{state}/")
        total += len(frames)
    return total


def build_icons() -> int:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    icon_dir = RAW_DIR / "icons"
    for raw_name, out_name in ICON_MAP.items():
        icon = square_pad(trim_alpha(load_raw(icon_dir / raw_name)))
        icon.resize((256, 256), Image.LANCZOS).save(ICON_DIR / out_name)
        print(f"  icons/{raw_name:24} -> icons/{out_name}")

    ico = square_pad(trim_alpha(load_raw(icon_dir / ICO_SOURCE)))
    ico.resize((256, 256), Image.LANCZOS).save(ICON_DIR / "pattu.ico", sizes=ICO_SIZES)
    print(f"  icons/{ICO_SOURCE:24} -> icons/pattu.ico ({len(ICO_SIZES)} sizes)")
    return len(ICON_MAP) + 1


def main() -> int:
    if not RAW_DIR.exists():
        print(f"error: {RAW_DIR} not found", file=sys.stderr)
        return 1

    print(f"Preparing assets from {RAW_DIR}\n")
    posters = build_mascot_posters()
    frames = build_mascot_sequences()
    icons = build_icons()
    print(
        f"\nDone — {posters} poster frames at {CANVAS_W}x{CANVAS_H}, "
        f"{frames} animation frames, {icons} icons."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
