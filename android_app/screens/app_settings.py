"""Persist app settings (theme, palette, font size) across launches."""

import json
import os


_SETTINGS_FILE = "app_settings.json"

_DEFAULTS = {
    "theme_style": "Dark",
    "primary_palette": "Blue",
    "reader_font_size": 16,
}


def _path():
    """Resolve the settings file path (CWD is user_data_dir on Android)."""
    return os.path.join(os.getcwd(), _SETTINGS_FILE)


def load_settings():
    """Read saved settings, falling back to defaults for missing keys."""
    try:
        with open(_path(), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    merged = dict(_DEFAULTS)
    merged.update(data)
    return merged


def save_settings(**kwargs):
    """Merge *kwargs* into the persisted settings file (creates if needed)."""
    current = load_settings()
    current.update(kwargs)
    try:
        with open(_path(), "w", encoding="utf-8") as f:
            json.dump(current, f)
    except OSError:
        pass
