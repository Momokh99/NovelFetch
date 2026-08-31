import os
import sys


def _run_gui():
    # Android build: Buildozer launches THIS file (main.py at source.dir root).
    # Shared modules live in sources/ and core/ at the repo root, while the
    # KivyMD UI lives in gui/. Put the repo root on the path, then delegate.
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (here,):
        if p not in sys.path:
            sys.path.insert(0, p)
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
        _run_gui()
    else:
        from core.paths import ensure_data_dir

        ensure_data_dir(dev_root=os.path.dirname(os.path.abspath(__file__)))
        _run_tui()


if __name__ == "__main__":
    main()
