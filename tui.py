from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Input
from textual.containers import ScrollableContainer
from textual.binding import Binding

import finder


class JumpDialog(Screen):
    def __init__(self, chapters , callback):
        super().__init__()
        self.chapters = chapters
        self.callback = callback

    def compose(self):
        yield Static(f"Chapters: 1-{len(self.chapters)}")
        yield Input(placeholder="Enter a number  ")

    def on_input_submitted(self, event):
        try:
            num = int(event.value)
            if 1 <= num <=len(self.chapters):
                self.callback(num-1)
                self.app.pop_screen()
        except ValueError:
            pass


class ReaderScreen(Screen):
    BINDINGS = [
        ("n", "next_chapter", "Next"),
        ("p", "prev_chapter", "Prev"),
        ("j", "jump_chapter", "Jump"),
        ("d", "download", "Download"),
        ("q", "quit_reader", "Quit"),
    ]
    def __init__(self, chapters , slug , start=0):
        super().__init__()
        self.chapters = chapters
        self.slug = slug
        self.current = start

    def compose(self)->ComposeResult:
        yield Header(show_clock=False)
        with ScrollableContainer():
            yield Static(id="chapter-text")
        yield Footer()
    def on_mount(self):
        self.load_chapter()


    def load_chapter(self):
        ch = self.chapters[self.current]
        lines = finder.read_chapter(ch["url"])
        if lines is None:
            text = "Could not find chapter content."
        else:
            text = f"\n{'='*60}\n  Chapter {ch['num']}/{len(self.chapters)}: {ch['title']}\n{'='*60}\n\n"
            text += "\n\n".join(lines)
        self.query_one("#chapter-text").update(text)
        self.query_one(ScrollableContainer).scroll_home(animate=False)

    def action_next_chapter(self):
        if self.current < len(self.chapters) - 1:
            self.current += 1
            self.load_chapter()
    def action_prev_chapter(self):
        if self.current > 0:
            self.current -= 1
            self.load_chapter()
    def action_quit_reader(self):
        self.app.exit()
    def action_download(self):
        ch = self.chapters[self.current]
        ok = finder.save_chapter(ch["url"], ch["title"], self.slug)
        self.notify("Downloaded!" if ok else "Already saved.", timeout=2)
    def action_jump_chapter(self):
        self.app.push_screen(JumpDialog(self.chapters, self._jump_to))
    def _jump_to(self, idx):
        self.current = idx
        self.load_chapter()




class NovelReader(App):
    CSS = """
    Screen {
        background: $surface;
    }
    #chapter-text {
        margin: 1 2;
    }
    """


    def __init__(self, chapters, slug, start=0):
        super().__init__()
        self.chapters = chapters
        self.slug = slug
        self.start = start

    def on_mount(self):
        self.push_screen(ReaderScreen(self.chapters, self.slug, self.start))

if __name__=="__main__":
    NovelReader("gf", 'jgfd' ,0).run()

