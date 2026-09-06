"""Persist app settings (theme, palette, font size) across launches."""

import json
import os
import time

_SETTINGS_FILE = "app_settings.json"

_DEFAULTS = {
    "theme_style": "Dark",
    "primary_palette": "Blue",
    "reader_font_size": 16,
    "home_layout": "A",
    "read_indicator": "off",
    "card_grid_size": "medium",
    "show_continue_reading": True,
    "update_and_download": False,
}

# In-memory cache: avoids reading app_settings.json from disk on every
# row card (which would be O(n) reads for n library novels).
_cached_settings: dict | None = None
_cache_mtime: float = 0.0
_CACHE_TTL = 2.0  # seconds


def _path():
    """Resolve the settings file path (CWD is user_data_dir on Android)."""
    return os.path.join(os.getcwd(), _SETTINGS_FILE)


def load_settings():
    """Read saved settings, falling back to defaults for missing keys.

    Results are cached in memory and only re-read from disk if the file
    was modified (mtime changed) or the TTL (2 s) expired.  This avoids
    O(n) disk reads when building a large library grid.
    """
    global _cached_settings, _cache_mtime
    try:
        mtime = os.path.getmtime(_path())
    except OSError:
        mtime = 0.0
    now = time.monotonic()
    if (_cached_settings is not None
            and mtime == _cache_mtime
            and (now - _cache_mtime) < _CACHE_TTL):
        return _cached_settings
    try:
        with open(_path(), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    merged = dict(_DEFAULTS)
    merged.update(data)
    _cached_settings = merged
    _cache_mtime = mtime if mtime else now
    return merged


def save_settings(**kwargs):
    """Merge *kwargs* into the persisted settings file (creates if needed)."""
    global _cached_settings
    current = load_settings()
    current.update(kwargs)
    try:
        with open(_path(), "w", encoding="utf-8") as f:
            json.dump(current, f)
    except OSError:
        pass
    _cached_settings = current
