import os
import sys

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
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
        Clock.schedule_once(lambda dt: _orig_init_fbos(self) if self.width > 0 and self.height > 0 else None, 0)
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
        if platform == "android":
            os.chdir(self.user_data_dir)
        else:
            # Desktop: anchor CWD-relative data paths (novels/, app_settings.json,
            # progress.json) to the repo root so the app works from any launch
            # directory. All data modules use bare relative paths against CWD.
            os.chdir(_ROOT)

        from screens.app_settings import load_settings
        self._app_settings = load_settings()

        self.theme_cls.theme_style = self._app_settings["theme_style"]
        self.theme_cls.primary_palette = self._app_settings["primary_palette"]

        if platform == "android":
            try:
                from android import wakelock
                wakelock.acquire("novelfetch_reader")
            except Exception:
                pass

        from async_runner import async_loop
        async_loop.start()

        # Register custom widget classes in Factory AFTER any platform
        # chdir (Android user_data_dir) so that progress.py (imported
        # transitively) sees the correct working directory.
        import screens.browse  # noqa: F401  (Factory.register BrowseSection)
        import screens.topbar  # noqa: F401  (Factory.register TopBar)
        from screens import MainScreen
        return MainScreen()

    def on_start(self):
        from sources import REGISTRY
        self.current_source = list(REGISTRY.values())[0]

    def on_pause(self):
        from progress import progress
        progress.flush()
        return True

    def on_stop(self):
        from progress import progress
        progress.flush()
        from async_runner import async_loop
        async_loop.stop()

    def goto(self, name, **kwargs):
        self.root.goto(name, **kwargs)

    def back(self):
        self.root.back()

if __name__ == "__main__":
    NovelFetchApp().run()
