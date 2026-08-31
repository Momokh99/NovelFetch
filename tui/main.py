"""Textual TUI application (terminal frontend)."""

import os

from textual.app import App

from tui import MainMenu


class NovelFetchApp(App):
    TITLE = "NovelFetch"
    CSS_PATH = "novelfetch.tcss"

    def __init__(self):
        super().__init__()
        self.current_source = None

    def on_mount(self):
        self.push_screen(MainMenu())


def main():
    from core.paths import ensure_data_dir

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ensure_data_dir(dev_root=repo_root)
    NovelFetchApp().run()


if __name__ == "__main__":
    main()
