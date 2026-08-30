"""Development entry point with hot-reload enabled.

Usage:
    DEBUG=1 python android_app/main_dev.py
    # or
    python android_app/main_dev.py          # DEBUG defaults to True
"""
import os
import sys

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_APP_DIR)
for p in (_APP_DIR, _ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

# Force hot-reload on unless explicitly disabled
os.environ.setdefault("DEBUG", "1")

try:
    from kivymd.tools.hotreload.app import MDApp  # noqa: E402
    _HAS_HOTRELOAD = True
except ImportError:
    from kivymd.app import MDApp  # noqa: E402
    _HAS_HOTRELOAD = False
    print("[DEV] Hot-reload not available. Install watchdog: pip install watchdog")


class NovelFetchApp(MDApp):
    title = "NovelFetch"

    # KV files to watch — all .kv files in the kv/ directory
    KV_FILES = [
        os.path.join(_APP_DIR, "novelfetch.kv"),
    ]

    # Directories containing .kv files to watch
    KV_DIRS = [
        os.path.join(_APP_DIR, "kv"),
    ]

    # Python classes to watch for changes (key=class name, value=module path)
    CLASSES = {
        "MainScreen": "screens.main_screen",
        "HomeTab": "screens.home_tab",
        "SearchTab": "screens.search_tab",
        "SettingsTab": "screens.settings_tab",
        "UpdateTab": "screens.update",
        "HistoryTab": "screens.history",
        "NovelListScreen": "screens.novel_list",
        "ChapterListScreen": "screens.chapter_list",
        "ReaderScreen": "screens.reader",
        "DownloadProgressScreen": "screens.download_dialog",
        "DownloadPickerScreen": "screens.download_picker",
    }

    # Watch all subdirectories recursively
    AUTORELOADER_PATHS = [
        (".", {"recursive": True}),
        (_APP_DIR, {"recursive": True}),
    ]

    def build_app(self, first=False):
        """Called by the hot-reload tool instead of build()."""
        from kivy.resources import resource_add_path
        resource_add_path(_APP_DIR)

        if first:
            # First-time-only initialization
            from screens.app_settings import load_settings
            self._app_settings = load_settings()
            self.theme_cls.theme_style = self._app_settings["theme_style"]
            self.theme_cls.primary_palette = self._app_settings["primary_palette"]

            # Start async loop
            from async_runner import async_loop
            async_loop.start()

            # Register custom widget classes
            import screens.browse  # noqa: F401
            import screens.topbar  # noqa: F401

        from screens import MainScreen
        return MainScreen()

    def apply_state(self, state):
        """Reapply application state after a hot-reload rebuild."""
        # Restore state that was lost during reload
        pass

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


if __name__ == "__main__":
    NovelFetchApp().run()
