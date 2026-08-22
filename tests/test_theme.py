"""Tests for screens/theme.py — hsl_rgba color math (no Kivy needed)."""

import colorsys

from screens.theme import hsl_rgba, ACCENT, _DARK_SURFACE, _LIGHT_SURFACE, DIVIDER


def test_hsl_rgba_pure_red():
    assert hsl_rgba(0, 100, 50) == [1.0, 0.0, 0.0, 1.0]


def test_hsl_rgba_pure_green():
    result = hsl_rgba(120, 100, 50)
    assert result[1] == 1.0
    assert result[0] == 0.0
    assert result[2] == 0.0
    assert result[3] == 1.0


def test_hsl_rgba_pure_blue():
    result = hsl_rgba(240, 100, 50)
    assert result[2] == 1.0
    assert result[0] == 0.0
    assert result[1] == 0.0


def test_hsl_rgba_black():
    assert hsl_rgba(0, 0, 0) == [0.0, 0.0, 0.0, 1.0]


def test_hsl_rgba_white():
    assert hsl_rgba(0, 0, 100) == [1.0, 1.0, 1.0, 1.0]


def test_hsl_rgba_custom_alpha():
    result = hsl_rgba(0, 0, 0, 0.5)
    assert result[3] == 0.5


def test_hsl_rgba_default_alpha_is_one():
    result = hsl_rgba(180, 50, 50)
    assert result[3] == 1.0


def test_hsl_rgba_rounds_to_four_decimals():
    # The function rounds to 4 decimal places
    result = hsl_rgba(33, 67, 76)
    for v in result[:3]:
        assert len(str(v).split(".")[-1]) <= 4


def test_hsl_rgba_matches_colorsys():
    for h, s, l in [(0, 0, 0), (0, 100, 50), (120, 100, 50),
                     (240, 100, 50), (210, 95, 55), (180, 50, 50)]:
        expected_r, expected_g, expected_b = colorsys.hls_to_rgb(
            h / 360.0, l / 100.0, s / 100.0)
        result = hsl_rgba(h, s, l)
        assert result[0] == round(expected_r, 4)
        assert result[1] == round(expected_g, 4)
        assert result[2] == round(expected_b, 4)


def test_accent_is_blue():
    # ACCENT = hsl_rgba(210, 95, 55) → a vivid blue
    assert ACCENT[2] > ACCENT[0]  # blue channel dominant
    assert ACCENT[2] > ACCENT[1]
    assert ACCENT[3] == 1.0


def test_dark_surface_is_very_dark():
    assert all(v < 0.2 for v in _DARK_SURFACE[:3])


def test_light_surface_is_very_bright():
    assert all(v > 0.8 for v in _LIGHT_SURFACE[:3])


def test_divider_has_low_alpha():
    assert DIVIDER[3] == 0.35
