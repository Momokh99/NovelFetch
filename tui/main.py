"""Textual TUI application (terminal frontend)."""

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
    NovelFetchApp().run()


if __name__ == "__main__":
    main()
