import os
import sys


def _run_android_app():
    # Android build: Buildozer launches THIS file (main.py at source.dir root).
    # Shared modules (sources/, progress.py, ...) sit at the repo root, while
    # the KivyMD UI lives in android_app/. Put both on the path, then delegate.
    here = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.join(here, "android_app")
    for p in (app_dir, here):
        if p not in sys.path:
            sys.path.insert(0, p)
    from android_app.main import NovelFetchApp
    NovelFetchApp().run()


def _run_tui():
    from textual.app import App
    from screens import MainMenu

    class NovelFetchApp(App):
        TITLE = "NovelFetch"
        CSS_PATH = "novelfetch.tcss"
        def __init__(self):
            super().__init__()
            self.current_source = None

        def on_mount(self):
            self.push_screen(MainMenu())

    NovelFetchApp().run()


def main():
    # python-for-android sets ANDROID_ARGUMENT when running the packaged app;
    # the desktop TUI env may not even have kivy installed, so don't import it
    # at module scope.
    if os.environ.get("ANDROID_ARGUMENT"):
        _run_android_app()
    else:
        _run_tui()


if __name__ == "__main__":
    main()
