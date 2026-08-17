"""Every colour and stylesheet in one place.

Change the look of the whole app here rather than hunting through widget code.
Colours first, then the stylesheet strings built from them.
"""
from __future__ import annotations

# ── Palette ───────────────────────────────────────────────────────────────────

BG = "#1A1A1A"            # chat background
BG_BAR = "#111111"        # status bar
BG_INPUT = "#2A2A2A"      # text field
BG_BUBBLE_PATTU = "#2D2D2D"
BG_BUTTON_SECONDARY = "#444444"

ACCENT = "#0078D4"        # user bubbles, primary button
TEXT = "#E0E0E0"
TEXT_MUTED = "#888888"
TEXT_ON_ACCENT = "#FFFFFF"
BORDER = "#444444"
ERROR = "#FF6B6B"

FONT_FAMILY = "Segoe UI"
FONT_SIZE_PT = 10

RADIUS = 10
AVATAR_SIZE = 28          # profile icon beside Pattu's messages

# ── Stylesheets ───────────────────────────────────────────────────────────────

WINDOW_STYLE = f"background:{BG};"

STATUS_BAR_STYLE = (
    f"background:{BG_BAR}; color:{TEXT_MUTED}; padding:6px 12px; font-size:11px;"
)

SCROLL_AREA_STYLE = f"border:none; background:{BG};"

MESSAGES_STYLE = f"background:{BG};"

BUBBLE_USER_STYLE = (
    f"background:{ACCENT}; color:{TEXT_ON_ACCENT};"
    f"border-radius:{RADIUS}px; padding:8px 12px;"
)

BUBBLE_PATTU_STYLE = (
    f"background:{BG_BUBBLE_PATTU}; color:{TEXT};"
    f"border-radius:{RADIUS}px; padding:8px 12px;"
)

BUBBLE_STATUS_STYLE = f"color:{TEXT_MUTED}; font-style:italic; padding:2px 8px;"

BUBBLE_ERROR_STYLE = f"color:{ERROR}; font-style:italic; padding:2px 8px;"

INPUT_STYLE = (
    f"background:{BG_INPUT}; color:{TEXT}; border:1px solid {BORDER};"
    f"border-radius:8px; padding:8px 12px; font-size:13px;"
)

BUTTON_PRIMARY_STYLE = (
    f"background:{ACCENT}; color:{TEXT_ON_ACCENT};"
    "border-radius:8px; padding:8px 16px; font-weight:bold;"
)

BUTTON_SECONDARY_STYLE = (
    f"background:{BG_BUTTON_SECONDARY}; color:{TEXT};"
    "border-radius:8px; padding:8px 12px;"
)
