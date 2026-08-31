"""Resolve where NovelFetch keeps user data (novels/, progress, settings).

The data layer is intentionally CWD-relative (see core/progress.py, core/epub.py,
tui/*, gui/screens/app_settings.py). Both frontends chdir to a single stable
root at startup so those relative paths resolve identically across source,
frozen (PyInstaller), AppImage, Windows, and Android.

Resolution order (first match wins):

1. ``$NOVELFETCH_DATA_DIR`` -- explicit override for tests and tools.
2. ``android_user_data`` -- Kivy ``user_data_dir`` when running on Android.
3. Per-user home dir for self-contained packaging -- AppImage mounts are
   read-only and PyInstaller ``_MEIPASS`` is a throwaway temp dir, so writing
   next to the bundle would be lost or impossible; use ``~/.novelfetch``.
4. ``dev_root`` -- the repo root during source/dev runs, so existing data in
   ``novels/`` stays discoverable.
"""

import os
import sys

_HOME_DATA_DIR = os.path.join(os.path.expanduser("~"), ".novelfetch")


def is_frozen() -> bool:
    """True when running under PyInstaller (onefile bundles set sys.frozen)."""
    return bool(getattr(sys, "frozen", False))


def is_appimage() -> bool:
    """True when running inside an AppImage (runtime exports $APPDIR)."""
    return bool(os.environ.get("APPDIR") or os.environ.get("APPIMAGE"))


def home_data_dir() -> str:
    """Per-user data root, stable across packaging modes."""
    return _HOME_DATA_DIR


def data_dir(
    *, dev_root: str | None = None, android_user_data: str | None = None
) -> str:
    """Return the single writable data root (plus its enclosing dirs) for this run."""
    override = os.environ.get("NOVELFETCH_DATA_DIR")
    if override:
        return override
    if android_user_data:
        return android_user_data
    if is_appimage() or is_frozen():
        return _HOME_DATA_DIR
    return dev_root or os.getcwd()


def ensure_data_dir(
    *, dev_root: str | None = None, android_user_data: str | None = None
) -> str:
    """Resolve the data root, create it if needed, chdir into it, and return it.

    Both frontends call this at startup so the CWD-relative data layer resolves
    to one stable writable location in every packaging mode.
    """
    root = data_dir(dev_root=dev_root, android_user_data=android_user_data)
    os.makedirs(root, exist_ok=True)
    if root != os.getcwd():
        os.chdir(root)
    return root
