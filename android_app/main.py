import os
import sys

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_APP_DIR)

if _ROOT not in sys.path:
    sys.path.append(_ROOT)

from kivy.utils import platform
from kivymd.app import MDApp


class NovelFetchApp(MDApp):
    title = "NovelFetch"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_source = None

    def build(self):
        if platform == "android":
            os.chdir(self.user_data_dir)
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"

        from async_runner import async_loop
        async_loop.start()

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
