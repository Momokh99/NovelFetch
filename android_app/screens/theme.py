"""HSL-driven theme helpers and shared spacing constants.

All custom colors in the app come from here so the look stays consistent:
the accent is a single HSL hue and surfaces/placeholders/divider are derived
neutrals that adapt to dark/light. Material colors (nav, labels) still come
from theme_cls.primary_palette, chosen in the Settings palette dialog."""

from colorsys import hls_to_rgb

from kivy.metrics import dp

# ---- spacing ----

PAGE_PAD = dp(16)     # horizontal gutter of every screen's scroll content
SECTION_GAP = dp(8)   # vertical gap between content blocks
TAB_CONTENT_PAD = (dp(16), 0, dp(16), dp(16))  # gutters, no top gap under the TopBar
CARD_PAD = dp(12)     # inner padding of tappable result cards
CARD_GAP = dp(16)     # gap between a card's cover, text, and action
CARD_RADIUS = [14, 14, 14, 14]
COVER_RADIUS = [10, 10, 10, 10]
COVER_THUMB = dp(70)  # result-row cover width (novel/search lists)
COVER_TAB = dp(48)    # small tab cover width (updates/history rows)

# ---- color helpers ----

def hsl_rgba(h, s, l, a=1.0):
    """HSL (h: 0-360, s/l: 0-100) -> Kivy RGBA list with 0-1 floats."""
    r, g, b = hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
    return [round(r, 4), round(g, 4), round(b, 4), a]


ACCENT = hsl_rgba(210, 95, 55)   # vivid blue, the app's custom accent

_DARK_SURFACE = hsl_rgba(0, 0, 14)
_LIGHT_SURFACE = hsl_rgba(0, 0, 98)

DIVIDER = hsl_rgba(0, 0, 55, 0.35)


def _is_dark():
    from kivymd.app import MDApp
    app = MDApp.get_running_app()
    if app is None:
        return True
    return app.theme_cls.theme_style == "Dark"


def surface_color():
    """Neutral surface used for cover placeholders, slightly lifted from the
    screen background so cards read as distinct panels."""
    return _DARK_SURFACE if _is_dark() else _LIGHT_SURFACE