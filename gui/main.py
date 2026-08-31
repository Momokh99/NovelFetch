import os
import sys


def _app_dir() -> str:
    if getattr(sys, "frozen", False):
        # PyInstaller onefile extracts the entry script to the bundle root and
        # extracts bundled data (gui/) under sys._MEIPASS. Resolve assets from
        # the real bundle location, not the mis-pointed __file__.
        meipass = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(meipass, "gui")
    return os.path.dirname(os.path.abspath(__file__))


_APP_DIR = _app_dir()
_ROOT = os.path.dirname(_APP_DIR)


if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)
if _ROOT not in sys.path:
    sys.path.append(_ROOT)

from kivy.utils import platform
from kivymd.app import MDApp

# KivyMD 2.0: RectangularRippleBehavior.__init__ creates an FBO with
# self.size before the widget is laid out (size 0x0), which crashes on
# some desktop OpenGL drivers.  Patch it to defer until the widget has
# a real size.
from kivymd.uix.behaviors.ripple_behavior import RectangularRippleBehavior

_orig_init_fbos = RectangularRippleBehavior.init_fbos


def _safe_init_fbos(self):
    if self.width > 0 and self.height > 0:
        _orig_init_fbos(self)
    else:
        from kivy.clock import Clock

        Clock.schedule_once(
            lambda dt: (
                _orig_init_fbos(self) if self.width > 0 and self.height > 0 else None
            ),
            0,
        )


RectangularRippleBehavior.init_fbos = _safe_init_fbos


class NovelFetchApp(MDApp):
    title = "NovelFetch"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # KV includes (via #:include) and Builder.load_file resolve through
        # Kivy's resource path, not CWD.  Pin the app dir as a resource root
        # so kv/ includes find their targets without touching CWD, which must
        # stay at the launch directory so CWD-relative data paths (novels/)
        # resolve correctly.
        from kivy.resources import resource_add_path

        resource_add_path(_APP_DIR)
        self.kv_file = os.path.join(_APP_DIR, "novelfetch.kv")
        self.current_source = None

    def build(self):
        # Anchor CWD-relative data paths (novels/, app_settings.json,
        # progress.json) to a single stable root shared with the TUI:
        # Android user_data_dir, a per-user dir when frozen/AppImage (the
        # bundle's _MEIPASS/mount is throwaway or read-only), else the repo root.
        from core.paths import ensure_data_dir

        android_user_data = self.user_data_dir if platform == "android" else None
        ensure_data_dir(dev_root=_ROOT, android_user_data=android_user_data)
        from gui.screens.app_settings import load_settings

        self._app_settings = load_settings()

        self.theme_cls.theme_style = self._app_settings["theme_style"]
        self.theme_cls.primary_palette = self._app_settings["primary_palette"]

        if platform == "android":
            try:
                from android import wakelock

                wakelock.acquire("novelfetch_reader")
            except Exception:
                pass

        from gui.async_runner import async_loop

        async_loop.start()

        # Register custom widget classes in Factory AFTER any platform
        # chdir (Android user_data_dir) so that progress.py (imported
        # transitively) sees the correct working directory.
        import gui.screens.browse  # noqa: F401  (Factory.register BrowseSection)
        import gui.screens.topbar  # noqa: F401  (Factory.register TopBar)
        from gui.screens import MainScreen

        return MainScreen()

    def on_start(self):
        from sources import REGISTRY

        self.current_source = list(REGISTRY.values())[0]

    def on_pause(self):
        from core.progress import progress

        progress.flush()
        return True

    def on_stop(self):
        from core.progress import progress

        progress.flush()
        from gui.async_runner import async_loop

        async_loop.stop()

    def goto(self, name, **kwargs):
        self.root.goto(name, **kwargs)

    def back(self):
        self.root.back()


def main():
    NovelFetchApp().run()


if __name__ == "__main__":
    main()
