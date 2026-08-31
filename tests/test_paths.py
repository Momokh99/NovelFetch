"""Tests for core/paths.py data-root resolution."""

import os

from core import paths


def test_frozen_uses_home_data_dir(monkeypatch):
    monkeypatch.delenv("NOVELFETCH_DATA_DIR", raising=False)
    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    monkeypatch.setattr(paths, "is_appimage", lambda: False)
    assert paths.data_dir(dev_root="/tmp/repo") == paths.home_data_dir()


def test_appimage_uses_home_data_dir(monkeypatch):
    monkeypatch.delenv("NOVELFETCH_DATA_DIR", raising=False)
    monkeypatch.setattr(paths, "is_frozen", lambda: False)
    monkeypatch.setattr(paths, "is_appimage", lambda: True)
    assert paths.data_dir(dev_root="/tmp/repo") == paths.home_data_dir()


def test_android_user_data_wins_over_frozen(monkeypatch):
    monkeypatch.delenv("NOVELFETCH_DATA_DIR", raising=False)
    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    monkeypatch.setattr(paths, "is_appimage", lambda: False)
    assert (
        paths.data_dir(dev_root="/tmp/repo", android_user_data="/data/data/novelfetch")
        == "/data/data/novelfetch"
    )


def test_source_uses_dev_root(monkeypatch):
    monkeypatch.delenv("NOVELFETCH_DATA_DIR", raising=False)
    monkeypatch.setattr(paths, "is_frozen", lambda: False)
    monkeypatch.setattr(paths, "is_appimage", lambda: False)
    assert paths.data_dir(dev_root="/tmp/repo") == "/tmp/repo"


def test_env_override_wins_over_everything(monkeypatch):
    monkeypatch.setenv("NOVELFETCH_DATA_DIR", "/tmp/custom")
    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    monkeypatch.setattr(paths, "is_appimage", lambda: True)
    assert (
        paths.data_dir(dev_root="/tmp/repo", android_user_data="/data/data/novelfetch")
        == "/tmp/custom"
    )


def test_ensure_data_dir_creates_and_chdirs(tmp_path, monkeypatch):
    monkeypatch.delenv("NOVELFETCH_DATA_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "data"
    root = paths.ensure_data_dir(dev_root=str(target))
    assert os.path.isdir(root)
    assert os.getcwd() == str(target)
