"""Tests for the Home tab's summary helpers."""

from gui.screens.app_settings import save_settings
from gui.screens.home_tab import _count_summary, _grid_cols


def test_count_summary_singular():
    assert _count_summary(1, 0) == "1 novel"


def test_count_summary_plural():
    assert _count_summary(3, 0) == "3 novels"


def test_count_summary_with_tracked():
    assert _count_summary(3, 2) == "3 novels · 2 tracked"


def test_count_summary_tracked_only_one():
    assert _count_summary(1, 1) == "1 novel · 1 tracked"


def test_grid_cols_defaults_to_medium(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert _grid_cols() == 2


def test_grid_cols_follows_setting(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_settings(card_grid_size="small")
    assert _grid_cols() == 3
    save_settings(card_grid_size="large")
    assert _grid_cols() == 1