import asyncio
import os

from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import (
    Footer,
    Input,
    Label,
    ListItem,
    ListView,
    ProgressBar,
    Static,
)

from core.epub import _export_epub
from core.progress import _slug_to_title
from core.translation import _translate_text
from tui.shared import CustomHeader, LanguagePicker
from tui.utils import _get_source


class DownloadDialog(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Back"),
        Binding("e", "toggle_epub", "EPUB"),
    ]

    def __init__(self, chapters, slug, source, current_idx=None, has_translation=False):
        super().__init__()
        self.chapters = chapters
        self.slug = slug
        self.source = source
        self.current_idx = current_idx
        self.has_translation = has_translation
        self._epub_mode = False

    def compose(self):
        with Vertical(classes="dialog-overlay"):
            with Vertical(classes="dialog-box"):
                yield Static("Download  |  EPUB: OFF  (e)", id="dl-epub-status", classes="title")
                items = []
                if self.current_idx is not None:
                    items.append(ListItem(Label("Download Current")))
                    if self.has_translation:
                        items.append(ListItem(Label("Download Current (Translated)")))
                items.append(ListItem(Label("Download All")))
                items.append(ListItem(Label("Download All (Translated)")))
                items.append(ListItem(Label("Download Range...")))
                items.append(ListItem(Label("Download Range (Translated)...")))
                yield ListView(*items, id="dl-options")
    def on_mount(self):
        self.query_one("#dl-options", ListView).focus()
    def action_toggle_epub(self):
        self._epub_mode = not self._epub_mode
        s = "ON" if self._epub_mode else "OFF"
        self.query_one("#dl-epub-status", Static).update(f"Download  |  EPUB: {s}  (e)")
    def on_list_view_selected(self, event):
        idx = event.list_view.index
        if idx is None:
            return
        offset = 0
        if self.current_idx is not None:
            if idx == 0:
                asyncio.create_task(self._save_current(self.app))
                self.app.pop_screen()
                return
            offset += 1
            if self.has_translation:
                if idx == 1:
                    asyncio.create_task(self._save_current_translated(self.app))
                    self.app.pop_screen()
                    return
                offset += 1
        action_idx = idx - offset
        ch, sl, src = self.chapters, self.slug, self.source
        app = self.app
        epub = self._epub_mode
        self.app.pop_screen()
        if action_idx == 0:
            S = DownloadEPUBScreen if epub else DownloadProgressScreen
            app.push_screen(S(ch, sl, src))
        elif action_idx == 1:
            def choose_language(lang):
                if not lang:
                    return
                screen = (
                    DownloadEPUBScreen(ch, sl, src, translate=True, lang=lang)
                    if epub
                    else DownloadProgressScreen(
                        ch, sl, src, translate=True, lang=lang
                    )
                )
                app.push_screen(ConfirmScreen(
                    "Translating all chapters is slow. Continue?",
                    lambda: app.push_screen(screen),
                ))

            app.push_screen(LanguagePicker(), choose_language)
        elif action_idx == 2:
            app.push_screen(DownloadChaptersScreen(ch, sl, src, epub=epub))
        elif action_idx == 3:
            self._download_range_translated(ch, sl, src, app, epub=epub)

    def _download_range_translated(self, chapters, slug, source, app, epub=False):
        def choose_language(lang):
            if not lang:
                return
            app.push_screen(ConfirmScreen(
                "Translating chapters is slow. Continue?",
                lambda: app.push_screen(DownloadChaptersScreen(
                    chapters, slug, source, translate=True, lang=lang, epub=epub
                )),
            ))

        app.push_screen(LanguagePicker(), choose_language)

    async def _save_current(self, app):
        try:
            ch = self.chapters[self.current_idx]
            src = self.source
            if src is None:
                app.notify("No source available.", timeout=3)
                return
            ok = await src.save_chapter(ch["url"], ch["title"], self.slug)
            app.notify("Downloaded!" if ok else "Already saved.", timeout=2)
        except Exception:
            app.notify("Failed to download chapter.", timeout=3)

    async def _save_current_translated(self, app):
        try:
            ch = self.chapters[self.current_idx]
            src = self.source
            if src is None:
                app.notify("No source available.", timeout=3)
                return
            lines = await src.read_chapter(ch["url"])
            if lines is None:
                app.notify("Failed to read chapter.", timeout=3)
                return
            text = "\n\n".join(lines)
            app.push_screen(LanguagePicker(), lambda lang: (
                lang and asyncio.create_task(self._do_save_translated(lang, app))
            ))
        except Exception:
            app.notify("Failed to read chapter for translation.", timeout=3)

    async def _do_save_translated(self, lang, app):
        try:
            ch = self.chapters[self.current_idx]
            src = self.source
            if src is None:
                app.notify("No source available.", timeout=3)
                return
            lines = await src.read_chapter(ch["url"])
            if lines is None:
                app.notify("Failed to read chapter.", timeout=3)
                return
            text = "\n\n".join(lines)
            translated = await asyncio.to_thread(_translate_text, text, lang)
            if not translated:
                app.notify("Translation failed.", timeout=3)
                return
            safe_title = ch["title"].replace("/", "-").replace(" ", "_")
            path = f"novels/{self.slug}/{safe_title}_{lang}.txt"
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(translated)
            app.notify(f"Translated ({lang}) saved.", timeout=2)
        except Exception:
            app.notify("Failed to save translated chapter.", timeout=3)

    def action_dismiss(self):
        self.app.pop_screen()



class DownloadChaptersScreen(Screen):
    BINDINGS = [Binding("escape", "cancel", "Back")]

    def __init__(self, chapters, slug, source, translate=False, lang="ar", epub=False):
        super().__init__()
        self.chapters = chapters
        self.slug = slug
        self.source = source
        self.translate = translate
        self._lang = lang
        self._epub = epub

    def compose(self):
        with Vertical(classes="dialog-overlay"):
            with Vertical(classes="dialog-box"):
                label = "Download Chapters (Translated)" if self.translate else "Download Chapters"
                yield Static(label, classes="title")
                yield Static("Range: 1-50  |  List: 1,3,5  |  Blank: all", classes="title")
                yield Input(placeholder="Type a range, list, or press Enter for all")

    def on_mount(self):
        self.query_one(Input).focus()

    def on_input_submitted(self, event):
        selected = self._parse(event.value)
        filtered = [ch for ch in self.chapters if ch["num"] in selected] if selected else self.chapters
        self.app.pop_screen()
        if filtered:
            S = DownloadEPUBScreen if self._epub else DownloadProgressScreen
            self.app.push_screen(S(filtered, self.slug, self.source, translate=self.translate, lang=self._lang))
        else:
            self.notify("No matching chapters.", timeout=2)

    def _parse(self, text):
        text = text.strip()
        if not text:
            return None
        nums = set()
        for part in text.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                try:
                    nums.update(range(int(a.strip()), int(b.strip()) + 1))
                except ValueError:
                    pass
            else:
                try:
                    nums.add(int(part))
                except ValueError:
                    pass
        return sorted(nums)

    def action_cancel(self):
        self.app.pop_screen()




class DownloadProgressScreen(Screen):
    BINDINGS = [Binding("escape", "pop", "Close")]

    def __init__(self, chapters: list, slug: str, source=None, translate=False, lang="ar"):
        super().__init__()
        self.chapters = chapters
        self.slug = slug
        self._done = False
        self.source = source or _get_source(slug)
        self.translate = translate
        self._lang = lang

    def compose(self):
        yield CustomHeader()
        yield Static("Downloading...", classes="title")
        yield Static("", id="dl-novel")
        yield ProgressBar(total=len(self.chapters), id="dl-bar")
        yield Static("", id="dl-status")
        yield Footer()

    def on_mount(self):
        self.query_one("#dl-novel").update(f"Slug: {self.slug}")
        self.run_worker(self._download_all(), exclusive=True)

    async def _download_all(self):
        bar = self.query_one("#dl-bar")
        status = self.query_one("#dl-status")
        total = len(self.chapters)
        saved = 0
        src = self.source
        assert src is not None

        sem = asyncio.Semaphore(5)

        async def dl_chapter(ch):
            safe_title = ch["title"].replace("/", "-").replace(" ", "_")
            suffix = f"_{self._lang}" if self.translate else ""
            path = f"novels/{self.slug}/{safe_title}{suffix}.txt"
            if os.path.exists(path):
                return False
            async with sem:
                lines = await src.read_chapter(ch["url"])
                if lines is None:
                    return False
                text = "\n\n".join(lines)
                if self.translate:
                    translated = await asyncio.to_thread(_translate_text, text, self._lang)
                    if translated is None:
                        return False
                    text = translated
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                return True

        tasks = [dl_chapter(ch) for ch in self.chapters]
        for i, coro in enumerate(asyncio.as_completed(tasks), 1):
            ok = await coro
            if ok:
                saved += 1
            bar.progress = saved
            status.update(f"({i}/{total}) — {saved} saved")

        status.update(f"Done — {saved}/{total} saved.")
        self._done = True
        self.notify(f"Downloaded {saved}/{total} chapters.", timeout=3)

    def action_pop(self):
        self.app.pop_screen()


class DownloadEPUBScreen(Screen):
    BINDINGS = [Binding("escape", "pop", "Close")]

    def __init__(self, chapters, slug, source=None, translate=False, lang="ar"):
        super().__init__()
        self.chapters = chapters
        self.slug = slug
        self._done = False
        self.source = source or _get_source(slug)
        self.translate = translate
        self._lang = lang

    def compose(self):
        yield CustomHeader()
        yield Static("Downloading EPUB...", classes="title")
        yield Static("", id="dl-novel")
        yield ProgressBar(total=len(self.chapters), id="dl-bar")
        yield Static("", id="dl-status")
        yield Footer()

    def on_mount(self):
        self.query_one("#dl-novel").update(f"Novel: {_slug_to_title(self.slug)}")
        self.run_worker(self._download_all(), exclusive=True)

    async def _download_all(self):
        bar = self.query_one("#dl-bar")
        status = self.query_one("#dl-status")
        total = len(self.chapters)
        src = self.source
        assert src is not None
        sem = asyncio.Semaphore(5)
        results = []

        async def dl_chapter(ch):
            async with sem:
                lines = await src.read_chapter(ch["url"])
                if lines is None:
                    return None
                text = "\n\n".join(lines)
                if self.translate:
                    translated = await asyncio.to_thread(_translate_text, text, self._lang)
                    if translated is None:
                        return None
                    text = translated
                return (ch["title"], text)

        tasks = [dl_chapter(ch) for ch in self.chapters]
        for i, coro in enumerate(asyncio.as_completed(tasks), 1):
            r = await coro
            if r is not None:
                results.append(r)
            bar.progress = i
            status.update(f"Downloaded ({i}/{total})")

        status.update("Packaging EPUB...")
        try:
            out = await _export_epub(self.slug, self.source, chapters=results)
        except ImportError:
            status.update("ebooklib not installed. Run: pip install ebooklib")
            self.notify("ebooklib not installed. Run: pip install ebooklib", timeout=5)
            return
        if out:
            status.update(f"Saved: {out}")
            self.notify(f"EPUB saved: {out}", timeout=5)
        else:
            status.update("Failed to create EPUB")
            self.notify("EPUB creation failed.", timeout=3)
        self._done = True

    def action_pop(self):
        self.app.pop_screen()


class ConfirmScreen(Screen):
    BINDINGS = [Binding("escape", "no", "No")]

    def __init__(self, message, callback):
        super().__init__()
        self.message = message
        self.callback = callback
    def compose(self):
        with Vertical(classes="dialog-overlay"):
            with Vertical(classes="dialog-box"):
                yield Static(self.message, classes="title")
                yield ListView(
                    ListItem(Label("Yes")),
                    ListItem(Label("No")),
                )

    def on_mount(self):
        self.query_one(ListView).focus()

    def on_list_view_selected(self, event):
        app = self.app
        self.app.pop_screen()
        if event.list_view.index == 0:
            self.callback()





