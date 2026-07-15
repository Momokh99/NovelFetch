from textual.screen import Screen
from textual.binding import Binding
from textual.app import ComposeResult
from textual.widgets import Static, Footer
from textual.containers import ScrollableContainer
from screens.shared import CustomHeader, LanguagePicker, JumpDialog
from screens.download import DownloadDialog
from screens.utils import _get_source
from screens.main_menu import MainMenu
from progress import progress
from translation import _translate_text
import asyncio
import os


class LocalReaderScreen(Screen):
    BINDINGS = [
        ("n", "next_chapter", "Next"),
        ("p", "prev_chapter", "Prev"),
        ("t", "translate", "Translate"),
        ("r", "revert", "Revert"),
        ("q", "quit_reader", "Quit"),
        ("h", "home", "Home"),
         ("d", "download_dialog", "Download"),
    ]

    def __init__(self, files: list, slug: str, start=0):
        super().__init__()
        self.files = files
        self.slug = slug
        self.current = start
        self._original_text = ""
        self._translated_text = ""

    def compose(self):
        yield CustomHeader()
        yield Static(id="chapter-header")
        with ScrollableContainer():
            yield Static(id="local-text")
        yield Footer()
    def on_mount(self):
        self.load_chapter()
        self.query_one(ScrollableContainer).focus()

    def load_chapter(self):
        fpath = os.path.join("novels", self.slug, self.files[self.current])
        title = os.path.basename(self.files[self.current]).replace(".txt", "").replace("_", " ").title()
        try:
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
        except Exception:
            content = "Could not read chapter."
        text = f"\n{'='*60}\n  {title}\n{'='*60}\n\n{content}"
        self._original_text = text
        self._translated_text = ""
        self.query_one("#chapter-header").update(f"{title}  ({self.current + 1}/{len(self.files)})")
        self.query_one("#local-text").remove_class("rtl")
        self.query_one("#local-text").update(text)
        self.query_one(ScrollableContainer).scroll_home(animate=False)
        progress.mark_seen(self.slug, self.current)

    def action_next_chapter(self):
        if self.current < len(self.files) - 1:
            self.current += 1
            self.load_chapter()

    def action_prev_chapter(self):
        if self.current > 0:
            self.current -= 1
            self.load_chapter()

    def action_quit_reader(self):
        self.app.pop_screen()
    def action_home(self):
        self.app.switch_screen(MainMenu())

    async def action_translate(self):
        if not self._original_text:
            return
        self.app.push_screen(LanguagePicker(), self._on_lang)
    def action_download_dialog(self):
        self.run_worker(self._do_download_dialog(), exclusive=True)

    async def _do_download_dialog(self):
        from screens.utils import _get_chapters
        source = _get_source(self.slug)
        if not source:
            self.notify("No source found for this novel.", timeout=3)
            return
        try:
            chapters = await _get_chapters(
                source, self.slug.split(":", 1)[-1] if ":" in self.slug else self.slug
            )
        except Exception:
            self.notify("Failed to fetch chapters. Check network.", timeout=3)
            return
        if not chapters:
            self.notify("Could not fetch chapters.", timeout=3)
            return
        self.app.push_screen(DownloadDialog(
            chapters, self.slug, source,
            current_idx=self.current,
            has_translation=bool(self._translated_text),
        ))
    def _on_lang(self, lang):
        if not lang:
            return
        self.run_worker(self._do_translate(lang), exclusive=True)

    async def _do_translate(self, lang):
        translated = await asyncio.to_thread(_translate_text, self._original_text, lang)
        if translated:
            self._translated_text = translated
            self.query_one("#local-text").update(translated)
            if lang == "ar":
                self.query_one("#local-text").add_class("rtl")
            else:
                self.query_one("#local-text").remove_class("rtl")
        else:
            self.notify("Translation failed. Check internet.", timeout=3)

    def action_revert(self):
        if self._original_text:
            self.query_one("#local-text").update(self._original_text)
            self.query_one("#local-text").remove_class("rtl")


class ReaderScreen(Screen):
    BINDINGS = [
        ("n", "next_chapter", "Next"),
        ("p", "prev_chapter", "Prev"),
        ("j", "jump_chapter", "Jump"),
        ("d", "download_dialog", "Download"),
        ("t", "translate", "Translate"),
        ("r", "revert", "Revert"),
        ("q", "quit_reader", "Quit"),
        ("h", "home", "Home"),
    ]
    def __init__(self, chapters, slug, start=0, source=None):
        super().__init__()
        self.chapters = chapters
        self.slug = slug
        self.source = source or _get_source(slug)
        self.current = start
        self._original_text = ""
        self._translated_text = ""

    def compose(self)->ComposeResult:
        yield CustomHeader()
        yield Static(id="chapter-header")
        with ScrollableContainer():
            yield Static(id="chapter-text")
        yield Footer()
    async def on_mount(self):
        await self.load_chapter()
        self.query_one(ScrollableContainer).focus()

    async def load_chapter(self):
        if self.source is None:
            self.notify("No source available.", timeout=3)
            self.app.pop_screen()
            return
        ch = self.chapters[self.current]
        try:
            lines = await self.source.read_chapter(ch["url"])
        except Exception:
            self.notify("Failed to load chapter. Check network.", timeout=3)
            text = "Could not load chapter content."
            lines = None
        if lines is None:
            text = "Could not find chapter content."
        else:
            text = f"\n{'='*60}\n  Chapter {ch['num']}/{len(self.chapters)}: {ch['title']}\n{'='*60}\n\n"
            text += "\n\n".join(lines)
        self._original_text = text
        self._translated_text = ""
        self.query_one("#chapter-header").update(f"Chapter {ch['num']}/{len(self.chapters)}: {ch['title']}")
        self.query_one("#chapter-text").remove_class("rtl")
        self.query_one("#chapter-text").update(text)
        self.query_one(ScrollableContainer).scroll_home(animate=False)
        progress.mark_seen(self.slug, self.current)

    async def action_next_chapter(self):
        if self.current < len(self.chapters) - 1:
            self.current += 1
            await self.load_chapter()
    async def action_prev_chapter(self):
        if self.current > 0:
            self.current -= 1
            await self.load_chapter()
    def action_quit_reader(self):
        self.app.pop_screen()
    def action_home(self):
        self.app.switch_screen(MainMenu())
    def action_download_dialog(self):
        self.app.push_screen(DownloadDialog(
            self.chapters, self.slug, self.source,
            current_idx=self.current,
            has_translation=bool(self._translated_text),
        ))
    def action_jump_chapter(self):
        self.app.push_screen(JumpDialog(self.chapters, self._jump_to))
    async def _jump_to(self, idx):
        self.current = idx
        await self.load_chapter()

    async def action_translate(self):
        if not self._original_text:
            return
        self.app.push_screen(LanguagePicker(), self._on_lang)

    def _on_lang(self, lang):
        if not lang:
            return
        self.run_worker(self._do_translate(lang), exclusive=True)

    async def _do_translate(self, lang):
        translated = await asyncio.to_thread(_translate_text, self._original_text, lang)
        if translated:
            self._translated_text = translated
            self.query_one("#chapter-text").update(translated)
            if lang == "ar":
                self.query_one("#chapter-text").add_class("rtl")
            else:
                self.query_one("#chapter-text").remove_class("rtl")
        else:
            self.notify("Translation failed. Check internet.", timeout=3)

    def action_revert(self):
        if self._original_text:
            self.query_one("#chapter-text").update(self._original_text)
            self.query_one("#chapter-text").remove_class("rtl")
