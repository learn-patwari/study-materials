"""
remove_bg.py — removes the dark background from assets/pattu.png
Run after saving the image: python remove_bg.py
Outputs: assets/pattu_transparent.png (use this as your mascot)
"""
from pathlib import Path
from PIL import Image
import numpy as np

INPUT  = Path("assets/pattu.png")
OUTPUT = Path("assets/pattu_transparent.png")


def remove_dark_background(img: Image.Image, threshold: int = 60, feather: int = 8) -> Image.Image:
    """Makes dark/black pixels transparent with smooth feathering at the edges."""
    rgba = img.convert("RGBA")
    data = np.array(rgba, dtype=np.float32)

    r, g, b, a = data[..., 0], data[..., 1], data[..., 2], data[..., 3]

    # Brightness of each pixel (0–255)
    brightness = (r * 0.299 + g * 0.587 + b * 0.114)

    # Also detect the blue glow (dark blue is still background)
    is_blue_glow = (b > r * 1.5) & (b > g * 1.1) & (brightness < 120)

    # Combine: dark pixels OR blue-glow pixels → transparent
    is_bg = (brightness < threshold) | is_blue_glow

    # Feather: pixels near the edge fade out instead of hard-cut
    alpha_scale = np.clip((brightness - threshold + feather) / feather, 0.0, 1.0)
    alpha_scale[is_bg] = 0.0

    data[..., 3] = (a * alpha_scale).astype(np.uint8)

    return Image.fromarray(data.astype(np.uint8), "RGBA")


def main():
    if not INPUT.exists():
        print(f"ERROR: {INPUT} not found. Save the Pattu image there first.")
        return

    print(f"Loading {INPUT} ...")
    img = Image.open(INPUT)
    print(f"  Size: {img.size}, Mode: {img.mode}")

    result = remove_dark_background(img)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.save(OUTPUT, "PNG")
    print(f"Saved transparent version → {OUTPUT}")
    print()
    print("Now update your .env or rename the file:")
    print(f"  rename {OUTPUT} → assets/pattu.png")
    print("  (or the mascot widget will pick up pattu_transparent.png if you rename it)")


if __name__ == "__main__":
    main()
