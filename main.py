import importlib
import os
import sys
import types
from typing import Any


def _ensure_kivy_window_backend():
    """Let KivyMD import on a Kivy built without SDL2.

    android_env's Kivy was compiled with USE_SDL2=0 (kivy/setupconfig.py),
    so kivy.core.window._window_sdl2 was never built and Kivy runs on the
    deprecated pygame provider. KivyMD's WindowController tries window_sdl2,
    then window_sdl3, and raises when neither exists — which crashed the app
    on the first mouse move. Register a stand-in only as a last resort;
    builds that have SDL2 (Android, official wheels) never reach it.
    """
    try:
        importlib.import_module("kivy.core.window.window_sdl2")
        return
    except ImportError:
        pass

    # KivyMD imports window_sdl2 then window_sdl3 at module load time. On a
    # USE_SDL2=0 build (Arch's pygame-based Kivy, or any pip wheel built
    # without SDL2) neither provider exists, so register a stand-in so the
    # import still succeeds. The stand-in does NOT create a real window; the
    # pygame provider must handle that below.
    stub: Any = types.ModuleType("kivy.core.window.window_sdl3")
    stub.WindowSDL = object
    sys.modules["kivy.core.window.window_sdl3"] = stub

    if _fix_pygame_window_resize():
        return

    # No real window provider is available (no SDL2 build and no pygame).
    # Exit with an actionable message instead of Kivy's "Unable to find any
    # valuable Window provider" traceback.
    raise SystemExit(
        "NovelFetch GUI could not find a usable Kivy window provider.\n"
        "This android_env was built against an interpreter that has no\n"
        "SDL2-backed Kivy (bootstrap compile, USE_SDL2=0) and no pygame.\n"
        "\n"
        "Rebuild the environment against the system interpreter on Arch:\n"
        "  sudo pacman -S python-kivy python-pygame\n"
        "  rm -rf android_env\n"
        "  make setup-android\n"
        "or, on any OS, pin a 3.10-3.14 interpreter:\n"
        "  make setup-android PYTHON=/usr/bin/python3.14\n"
    )


def _fix_pygame_window_resize():
    """Keep the pygame provider in sync with the real window size.

    WindowBase binds ``_size`` to ``trigger_create_window``, and
    WindowPygame.create_window() re-reads ``pygame.display.Info()`` — which
    pygame never refreshes for OpenGL windows. The compositor's resize is
    therefore overwritten with the stale width/height from
    ~/.kivy/config.ini, so the app paints only that corner of the window and
    leaves the rest transparent (the desktop wallpaper shows through).
    ``pygame.display.get_window_size()`` does track the live surface, so
    swap it in for the duration of ``create_window()``.
    """
    try:
        import pygame  # type: ignore
    except ImportError:
        return False
    try:
        from kivy.core.window.window_pygame import WindowPygame
    except ImportError:
        return False

    original = WindowPygame.create_window
    real_info = pygame.display.Info

    class _LiveInfo:
        def __init__(self):
            try:
                width, height = pygame.display.get_window_size()
            except Exception:
                info = real_info()
                width, height = info.current_w, info.current_h
            self.current_w = width
            self.current_h = height

    def create_window(self, *args, **kwargs):
        pygame.display.Info = _LiveInfo
        try:
            return original(self, *args, **kwargs)
        finally:
            pygame.display.Info = real_info

    WindowPygame.create_window = create_window

    return True


def _run_gui():
    # Android build: Buildozer launches THIS file (main.py at source.dir root).
    # Shared modules live in sources/ and core/ at the repo root, while the
    # KivyMD UI lives in gui/. Put the repo root on the path, then delegate.
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (here,):
        if p not in sys.path:
            sys.path.insert(0, p)
    # Must run before gui.main, which imports kivymd at module scope.
    _ensure_kivy_window_backend()
    from gui.main import NovelFetchApp

    NovelFetchApp().run()


def _run_tui():
    from tui.main import NovelFetchApp

    NovelFetchApp().run()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="NovelFetch launcher: choose the TUI or GUI frontend."
    )
    parser.add_argument(
        "app",
        nargs="?",
        default=None,
        choices=("tui", "gui"),
        help="frontend to launch; defaults to 'gui' on Android, 'tui' on desktop",
    )
    args = parser.parse_args()

    app = args.app
    is_android = bool(os.environ.get("ANDROID_ARGUMENT"))
    if app is None:
        # python-for-android sets ANDROID_ARGUMENT when running the packaged
        # app; the desktop TUI env may not even have kivy installed, so don't
        # import it at module scope.
        app = "gui" if is_android else "tui"

    if app == "gui":
        # Set CWD BEFORE launching the GUI so that module-level imports
        # (ProgressTracker, sources) see the correct data directory.
        from core.paths import ensure_data_dir

        here = os.path.dirname(os.path.abspath(__file__))
        if os.path.isdir(os.path.join(here, ".git")):
            ensure_data_dir(dev_root=here)
        else:
            ensure_data_dir()
        _run_gui()
    else:
        from core.paths import ensure_data_dir

        here = os.path.dirname(os.path.abspath(__file__))
        if os.path.isdir(os.path.join(here, ".git")):
            ensure_data_dir(dev_root=here)
        else:
            ensure_data_dir()
        _run_tui()


if __name__ == "__main__":
    main()
