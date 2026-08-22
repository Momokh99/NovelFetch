"""Tests for android_app/screens/app_settings.py persistence."""

import json

import pytest

from screens import app_settings


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_defaults_when_missing():
    s = app_settings.load_settings()
    assert s == dict(app_settings._DEFAULTS)


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
