"""Tests for gui/screens/app_settings.py persistence."""

import json

import pytest

from gui.screens import app_settings


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_defaults_when_missing():
    s = app_settings.load_settings()
    assert s == dict(app_settings._DEFAULTS)
    assert s["home_layout"] == "A"
    assert s["read_indicator"] == "off"
    assert s["card_grid_size"] == "medium"
    assert s["show_continue_reading"] is True


def test_layout_saved_and_loaded():
    app_settings.save_settings(home_layout="B")
    assert app_settings.load_settings()["home_layout"] == "B"


def test_home_layout_labels():
    from gui.screens.settings_tab import HOME_LAYOUTS, _home_layout_label
    assert len(HOME_LAYOUTS) == 2
    assert _home_layout_label("A") == "Cards"
    assert _home_layout_label("B") == "List"
    assert _home_layout_label("Z") == "Z"


def test_read_indicator_labels():
    from gui.screens.settings_tab import READ_INDICATORS, _read_indicator_label
    assert [k for k, _ in READ_INDICATORS] == [
        "off", "text", "linear", "percentage", "blocks", "dots", "wave"]
    assert _read_indicator_label("off") == "Off"
    assert _read_indicator_label("blocks") == "Segmented blocks"
    assert _read_indicator_label("zz") == "zz"


def test_grid_size_labels():
    from gui.screens.settings_tab import CARD_GRID_SIZES, _grid_size_label
    assert [k for k, _ in CARD_GRID_SIZES] == ["large", "medium", "small"]
    assert _grid_size_label("large") == "Large (1 per row)"
    assert _grid_size_label("medium") == "Medium (2 per row)"
    assert _grid_size_label("nope") == "nope"


def test_defaults_when_corrupt():
    open(app_settings._path(), "w").write("{not json")
    s = app_settings.load_settings()
    assert s == dict(app_settings._DEFAULTS)


def test_defaults_when_empty_file():
    open(app_settings._path(), "w").write("")
    s = app_settings.load_settings()
    assert s == dict(app_settings._DEFAULTS)


def test_save_and_load_roundtrip():
    app_settings.save_settings(primary_palette="Teal", reader_font_size=22)
    s = app_settings.load_settings()
    assert s["primary_palette"] == "Teal"
    assert s["reader_font_size"] == 22
    assert s["theme_style"] == "Dark"


def test_merge_preserves_existing_keys():
    app_settings.save_settings(theme_style="Light")
    app_settings.save_settings(reader_font_size=18)
    s = app_settings.load_settings()
    assert s["theme_style"] == "Light"
    assert s["reader_font_size"] == 18


def test_save_empty_kwargs_is_noop():
    app_settings.save_settings()
    s = app_settings.load_settings()
    assert s == dict(app_settings._DEFAULTS)


def test_unknown_keys_preserved():
    app_settings.save_settings(future_key=42)
    s = app_settings.load_settings()
    assert s["future_key"] == 42
    assert s["theme_style"] == "Dark"


def test_file_content_is_valid_json():
    app_settings.save_settings(reader_font_size=20)
    data = json.loads(open(app_settings._path()).read())
    assert data["reader_font_size"] == 20
    assert "theme_style" in data


def test_file_created_on_first_save(tmp_path):
    assert not (tmp_path / "app_settings.json").exists()
    app_settings.save_settings(reader_font_size=20)
    assert (tmp_path / "app_settings.json").exists()
