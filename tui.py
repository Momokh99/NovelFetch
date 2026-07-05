from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Input, RadioSet, RadioButton, ListView, ListItem, Label, LoadingIndicator, ProgressBar
from textual.containers import ScrollableContainer, Vertical
from textual.binding import Binding
import asyncio
import json
import os
from sources import REGISTRY
from deep_translator import GoogleTranslator

from sources.base import Source


GENRES = {
    "action-adventure": "Action",
    "adventure": "Adventure",
    "comedy": "Comedy",
    "drama": "Drama",
    "fantasy": "Fantasy",
    "horror": "Horror",
    "mystery": "Mystery",
    "romance": "Romance",
    "science-fiction": "Sci-Fi",
    "thriller": "Thriller",
    "wuxia": "Wuxia",
    "litrpg": "LitRPG",
    "gamelit": "GameLit",
    }

PROGRESS_FILE = "novels/progress.json"

def _slug_to_title(slug):
    raw = slug.split(":", 1)[-1] if ":" in slug else slug
    return raw.replace("-", " ").title()

def _get_source(slug):
    source_name = slug.split(":", 1)[0] if ":" in slug else None
    if source_name:
        return REGISTRY.get(source_name)
    return None

def _chapter_sort_key(fname):
    import re
    nums = re.findall(r"\d+", fname)
    return int(nums[0]) if nums else 0

def _load_progress():
    try:
        with open(PROGRESS_FILE) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    for slug, val in list(data.items()):
        if isinstance(val, int):
            data[slug] = {"last": val, "seen": [val]}
    return data

def _mark_seen(slug, idx):
    data = _load_progress()
    entry = data.get(slug, {"last": idx, "seen": []})
    entry["last"] = idx
    if idx not in entry["seen"]:
        entry["seen"].append(idx)
    data[slug] = entry
    os.makedirs(os.path.dirname(PROGRESS_FILE) or ".", exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def _get_last_read(slug):
    data = _load_progress()
    entry = data.get(slug)
    return entry["last"] if entry else None

def _get_seen(slug):
    data = _load_progress()
    entry = data.get(slug)
    return set(entry["seen"]) if entry else set()

def _scan_library():
    novels_dir = "novels"
    if not os.path.isdir(novels_dir):
        return []
    result = []
    for slug in sorted(os.listdir(novels_dir)):
        chap_dir = os.path.join(novels_dir, slug)
        if os.path.isdir(chap_dir):
            files = sorted(os.listdir(chap_dir))
            result.append({"slug": slug, "title": _slug_to_title(slug), "count": len(files)})
    return result

SETTINGS_FILE = "novels/settings.json"

def _load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_setting(key, val):
    data = _load_settings()
    data[key] = val
    os.makedirs(os.path.dirname(SETTINGS_FILE) or ".", exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)

LANGUAGES = {
    "Arabic": "ar", "Chinese": "zh-cn", "French": "fr", "German": "de",
    "Hindi": "hi", "Italian": "it", "Japanese": "ja", "Korean": "ko",
    "Portuguese": "pt", "Russian": "ru", "Spanish": "es", "Turkish": "tr",
}

def _chunk_text(text, maxlen=4800):
    paragraphs = text.split("\n\n")
    chunks, cur = [], ""
    for p in paragraphs:
        if len(p) > maxlen:
            sentences = p.replace("\n", " ").split(". ")
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                if len(cur) + len(s) + 2 > maxlen:
                    chunks.append(cur)
                    cur = s + "."
                else:
                    cur = (cur + " " + s + ".") if cur else (s + ".")
            continue
        if len(cur) + len(p) + 2 > maxlen:
            chunks.append(cur)
            cur = p
        else:
            cur = (cur + "\n\n" + p) if cur else p
    if cur:
        chunks.append(cur)
    return chunks

def _translate_text(text, target):
    try:
        translator = GoogleTranslator(source="auto", target=target)
        chunks = _chunk_text(text)
        if len(chunks) == 1:
            return translator.translate(text)
        translated = [translator.translate(c) for c in chunks]
        return "\n\n".join(translated)
    except Exception:
        return None

class MainMenu(Screen):
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("tab", "next_option", "", show=False),
        Binding("shift+tab", "prev_option", "", show=False),
    ]

    def compose(self):
        yield Header(show_clock=False)
        yield Static("""\
     ███╗   ██╗ ██████╗ ██╗   ██╗███████╗██╗     ██████╗ ██╗███╗   ██╗
     ████╗  ██║██╔═══██╗██║   ██║██╔════╝██║     ██╔══██╗██║████╗  ██║
     ██╔██╗ ██║██║   ██║██║   ██║█████╗  ██║     ██████╔╝██║██╔██╗ ██║
     ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══╝  ██║     ██╔══██╗██║██║╚██╗██║
     ██║ ╚████║╚██████╔╝ ╚████╔╝ ███████╗███████╗██████╔╝██║██║ ╚████║
     ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚══════╝╚══════╝╚═════╝ ╚═╝╚═╝  ╚═══╝""", classes="banner")
        with Vertical():
            yield Static("Source:", classes="title")
            yield Static("  ◆  " + list(REGISTRY.values())[0].label, id="source-label")
            yield Static("Action:", classes="title")
            yield RadioSet(
                RadioButton("Search by name"),
                RadioButton("Hot novels"),
                RadioButton("Latest releases"),
                RadioButton("Most popular"),
                RadioButton("Completed novels"),
                RadioButton("Browse by genre"),
                RadioButton("My Library"),
                id="action-selector"
            )
            yield LoadingIndicator(classes="loading")
        yield Footer()

    async def on_radio_set_changed(self, event: RadioSet.Changed):
        idx = event.index
        if idx in (1, 2, 3, 4):
            self.query_one("#action-selector", RadioSet).disabled = True
            self.query_one(LoadingIndicator).set_class(True, "-visible")
            try:
                source = self.app.current_source
                key = ["hot", "latest", "popular", "completed"][idx - 1]
                soup = await source.fetch_url(source.browse_urls[key])
                novels = source.extract_novel_rows(soup)
                self.app.push_screen(NovelListScreen(novels, source=source))
            except Exception:
                self.notify("Failed to fetch novels. Check your connection.", timeout=3)
            finally:
                self.query_one(LoadingIndicator).set_class(False, "-visible")
                self.query_one("#action-selector", RadioSet).disabled = False
        elif idx == 5:
            self.app.push_screen(GenreScreen(source=self.app.current_source))
        elif idx == 0:
            self.app.push_screen(SearchScreen(source=self.app.current_source))
        elif idx == 6:
            self.app.push_screen(MyLibraryScreen())

    def action_quit(self):
        self.app.exit()

    def action_next_option(self):
        self.query_one("#action-selector", RadioSet).action_next_button()

    def action_prev_option(self):
        self.query_one("#action-selector", RadioSet).action_previous_button()
    def on_mount(self):
        self.app.current_source = list(REGISTRY.values())[0]


class SearchScreen(Screen):
    BINDINGS = [
        Binding("escape", "clear_or_pop", "Back"),
        Binding("n", "next_page", "Next"),
        Binding("p", "prev_page", "Prev"),
    ]

    def __init__(self, source):
        super().__init__()
        self.source = source
        self._query = ""
        self._page = 1
        self._total_pages = 1
        self._results = []
        self._search_timer = None

    def compose(self):
        yield Header(show_clock=False)
        yield Input(placeholder="Search novels...")
        yield Static("", id="page-info")
        with ScrollableContainer():
            yield ListView()
            yield LoadingIndicator(classes="loading")
        yield Footer()

    def on_mount(self):
        self.query_one(Input).focus()

    def on_input_changed(self, event: Input.Changed):
        q = event.value.strip()
        if q == self._query:
            return
        self._query = q
        self._page = 1
        self._total_pages = 1
        self._results = []
        self._clear_list()
        self.query_one("#page-info").update("")
        if self._search_timer:
            self._search_timer.stop()
        if self._query:
            self._search_timer = self.set_timer(0.75, self._do_search)

    def _clear_list(self):
        lv = self.query_one(ListView)
        lv.clear()

    async def _do_search(self):
        if not self._query:
            return
        await self._fetch_page()

    async def _fetch_page(self):
        inp = self.query_one(Input)
        inp.disabled = True
        self.query_one(LoadingIndicator).set_class(True, "-visible")
        try:
            novels, total_pages = await self.source.search(self._query, self._page)
            self._results = novels
            self._total_pages = total_pages
            self._show_results(novels)
        except Exception:
            self.notify("Search failed. Check internet.", timeout=3)
        finally:
            inp.disabled = False
            self.query_one(LoadingIndicator).set_class(False, "-visible")

    def _show_results(self, novels):
        lv = self.query_one(ListView)
        lv.clear()
        for n in novels:
            sub = n.get("author", "")
            if n.get("latest"):
                sub += f"  ·  {n['latest']}"
            text = n["title"]
            if sub:
                text += f"\n{sub}"
            lv.append(ListItem(Label(text)))
        pi = self.query_one("#page-info")
        if not novels:
            pi.update("No novels found")
        elif self._total_pages > 1:
            pi.update(f"{len(novels)} results — Page {self._page}/{self._total_pages}")
        else:
            pi.update(f"{len(novels)} results")

    async def on_list_view_selected(self, event: ListView.Selected):
        idx = event.list_view.index
        if idx is None or idx >= len(self._results):
            return
        self.query_one(ListView).disabled = True
        self.query_one(LoadingIndicator).set_class(True, "-visible")
        try:
            slug = self._results[idx]["slug"]
            chapters = await self.source.fetch_chapters(slug)
            if chapters:
                self.app.push_screen(ChapterListScreen(chapters, self.source.qualify_slug(slug), source=self.source))
            else:
                self.notify("No chapters found.", timeout=3)
        finally:
            self.query_one(LoadingIndicator).set_class(False, "-visible")
            self.query_one(ListView).disabled = False

    def action_next_page(self):
        if self._page < self._total_pages:
            self._page += 1
            self._clear_list()
            asyncio.create_task(self._fetch_page())

    def action_prev_page(self):
        if self._page > 1:
            self._page -= 1
            self._clear_list()
            asyncio.create_task(self._fetch_page())

    def action_clear_or_pop(self):
        inp = self.query_one(Input)
        if inp.value:
            inp.value = ""
            inp.post_message(Input.Changed(inp, ""))
        else:
            self.app.pop_screen()

    def action_pop(self):
        self.app.pop_screen()




class NovelListScreen(Screen):
    BINDINGS = [Binding("escape", "pop", "Back")]

    def __init__(self, novels: list, source=None):
        super().__init__()
        self.novels = novels
        self.source = source

    def compose(self):
        yield Header(show_clock=False)
        yield Static("Novels", classes="title")
        with ScrollableContainer():
            items = []
            for n in self.novels:
                sub = ""
                if n.get("author"):
                    sub += n["author"]
                if n.get("latest"):
                    sub += f"  ·  {n['latest']}"
                text = n["title"]
                if sub:
                    text += f"\n{sub}"
                items.append(ListItem(Label(text)))
            yield ListView(*items)
            yield LoadingIndicator(classes="loading")
        yield Footer()
    async def on_list_view_selected(self, event: ListView.Selected):
        self.query_one(ListView).disabled = True
        self.query_one(LoadingIndicator).set_class(True, "-visible")
        try:
            novel = self.novels[event.list_view.index]
            slug = novel["slug"]
            source = self.source or _get_source(slug)
            if not source:
                self.notify("No source found for this novel.", timeout=3)
                return
            bare = slug.split(":", 1)[-1] if ":" in slug else slug
            chapters = await source.fetch_chapters(bare)
            if chapters:
                self.app.push_screen(ChapterListScreen(chapters, source.qualify_slug(bare), source=source))
            else:
                self.notify("No chapters found.", timeout=3)
        finally:
            self.query_one(LoadingIndicator).set_class(False, "-visible")
            self.query_one(ListView).disabled = False

    def on_mount(self):
        self.query_one(ListView).focus()

    def action_pop(self):
        self.app.pop_screen()

class ChapterListScreen(Screen):

    def __init__(self, chapters: list, slug: str, source=None):
        super().__init__()
        self.chapters = chapters
        self.slug = slug
        self.source = source
    BINDINGS = [
        Binding("escape", "pop", "Back"),
        Binding("c", "continue_reading", "Continue"),
        Binding("d", "download_all", "Download All"),
    ]
    def compose(self):
        yield Header(show_clock=False)
        yield Static(f"Chapters: 1-{len(self.chapters)}", classes="title")
        seen = _get_seen(self.slug)
        items = [ListItem(Label(("✓ " if i in seen else "  ") + c["title"])) for i, c in enumerate(self.chapters)]
        with ScrollableContainer():
            yield ListView(*items)
        yield Footer()
    def on_list_view_selected(self, event: ListView.Selected):
        idx = event.list_view.index
        self.app.push_screen(ReaderScreen(self.chapters, self.slug, source=self.source, start=idx))
    def on_mount(self):
        self.query_one(ListView).focus()

    def action_continue_reading(self):
        idx = _get_last_read(self.slug)
        if idx is not None and 0 <= idx < len(self.chapters):
            self.app.push_screen(ReaderScreen(self.chapters, self.slug, source=self.source, start=idx))
        else:
            self.notify("No saved progress.", timeout=2)

    def action_download_all(self):
        self.app.push_screen(DownloadProgressScreen(self.chapters, self.slug, source=self.source))

    def action_pop(self):
        self.app.pop_screen()

class GenreScreen(Screen):
    BINDINGS = [Binding("escape", "pop", "Back")]
    def __init__(self, source):
        super().__init__()
        self.source = source
    def compose(self):
        yield Header(show_clock=False)
        yield Static("Genres", classes="title")
        with ScrollableContainer():
            yield ListView(*[ListItem(Label(name)) for name in GENRES.values()])
            yield LoadingIndicator(classes="loading")
        yield Footer()

    async def on_list_view_selected(self, event: ListView.Selected):
        self.query_one(ListView).disabled = True
        self.query_one(LoadingIndicator).set_class(True, "-visible")
        try:
            slug = list(GENRES.keys())[event.list_view.index]
            novels = await self.source.browse_genre(slug)
            if novels:
                self.app.push_screen(NovelListScreen(novels, source=self.source))
            else:
                self.notify("No results.", timeout=3)
        except Exception:
            self.notify("Failed to load genre. Check your connection.", timeout=3)
        finally:
            self.query_one(LoadingIndicator).set_class(False, "-visible")
            self.query_one(ListView).disabled = False

    def on_mount(self):
        self.query_one(ListView).focus()

    def action_pop(self):
        self.app.pop_screen()

class MyLibraryScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop", "Back"),
        Binding("x", "delete", "Delete"),
    ]

    def compose(self):
        yield Header(show_clock=False)
        yield Static("My Library", classes="title")
        novels = _scan_library()
        if not novels:
            yield Static("No downloaded novels found.", classes="title")
        else:
            items = []
            for n in novels:
                last = _get_last_read(n["slug"])
                suffix = f" · Last: Ch. {last + 1}" if last is not None else ""
                items.append(ListItem(Label(f"{n['title']}  ({n['count']} ch.){suffix}")))
            with ScrollableContainer():
                yield ListView(*items)
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected):
        novels = _scan_library()
        if event.list_view.index < len(novels):
            self.app.push_screen(LocalChapterScreen(novels[event.list_view.index]["slug"]))

    def on_mount(self):
        try:
            self.query_one(ListView).focus()
        except Exception:
            pass

    def action_delete(self):
        lv = self.query_one(ListView)
        idx = lv.index
        if idx is None:
            return
        novels = _scan_library()
        if idx >= len(novels):
            return
        slug = novels[idx]["slug"]
        if getattr(self, "_pending", None) == slug:
            import shutil
            shutil.rmtree(os.path.join("novels", slug))
            self._pending = None
            self.notify(f"Deleted {_slug_to_title(slug)}", timeout=3)
            self.app.pop_screen()
            self.app.push_screen(MyLibraryScreen())
        else:
            self._pending = slug
            self.notify(f"Press x again to delete {_slug_to_title(slug)}", timeout=3)

    def action_pop(self):
        self._pending = None
        self.app.pop_screen()

class LocalChapterScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop", "Back"),
        Binding("c", "continue_reading", "Continue"),
        Binding("d", "download_all", "Download All"),
        Binding("x", "delete", "Delete"),
    ]

    def __init__(self, slug: str):
        super().__init__()
        self.slug = slug
        self.files = []

    def compose(self):
        yield Header(show_clock=False)
        yield Static(_slug_to_title(self.slug), classes="title")
        with ScrollableContainer():
            yield ListView(id="local-chapters")
        yield Footer()

    def on_mount(self):
        chap_dir = os.path.join("novels", self.slug)
        if os.path.isdir(chap_dir):
            self.files = sorted(os.listdir(chap_dir), key=_chapter_sort_key)
            lv = self.query_one("#local-chapters", ListView)
            seen = _get_seen(self.slug)
            for i, fname in enumerate(self.files):
                title = fname.replace(".txt", "").replace("_", " ").title()
                prefix = "✓ " if i in seen else "  "
                lv.mount(ListItem(Label(prefix + title)))
            lv.focus()

    def on_list_view_selected(self, event: ListView.Selected):
        idx = event.list_view.index
        if idx < len(self.files):
            self.app.push_screen(LocalReaderScreen(self.files, self.slug, start=idx))

    def action_delete(self):
        lv = self.query_one("#local-chapters", ListView)
        idx = lv.index
        if idx is None or idx >= len(self.files):
            return
        fname = self.files[idx]
        if getattr(self, "_pending", None) == fname:
            os.remove(os.path.join("novels", self.slug, fname))
            self._pending = None
            self.notify("Deleted", timeout=2)
            self.app.pop_screen()
            self.app.push_screen(LocalChapterScreen(self.slug))
        else:
            self._pending = fname
            self.notify("Press x again to delete", timeout=3)

    def action_continue_reading(self):
        idx = _get_last_read(self.slug)
        if idx is not None and 0 <= idx < len(self.files):
            self.app.push_screen(LocalReaderScreen(self.files, self.slug, start=idx))
        else:
            self.notify("No saved progress.", timeout=2)

    async def action_download_all(self):
        source = _get_source(self.slug)
        if not source:
            self.notify("No source found for this novel.", timeout=3)
            return
        chapters = await source.fetch_chapters(
            self.slug.split(":", 1)[-1] if ":" in self.slug else self.slug
        )
        if chapters:
            self.app.push_screen(DownloadProgressScreen(chapters, self.slug, source=source))
        else:
            self.notify("Could not fetch chapters.", timeout=3)

    def action_pop(self):
        self._pending = None
        self.app.pop_screen()

class LocalReaderScreen(Screen):
    BINDINGS = [
        ("n", "next_chapter", "Next"),
        ("p", "prev_chapter", "Prev"),
        ("t", "translate", "Translate"),
        ("r", "revert", "Revert"),
        ("q", "quit_reader", "Quit"),
        ("h", "home", "Home"),
    ]

    def __init__(self, files: list, slug: str, start=0):
        super().__init__()
        self.files = files
        self.slug = slug
        self.current = start
        self._original_text = ""
        self._translated_text = ""

    def compose(self):
        yield Header(show_clock=False)
        yield Static(id="chapter-header")
        with ScrollableContainer():
            yield Static(id="local-text")
        yield Footer()

    def on_mount(self):
        self.load_chapter()

    def load_chapter(self):
        fpath = os.path.join("novels", self.slug, self.files[self.current])
        title = self.files[self.current].replace(".txt", "").replace("_", " ").title()
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
        _mark_seen(self.slug, self.current)

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

    def _on_lang(self, lang):
        if not lang:
            return
        asyncio.create_task(self._do_translate(lang))

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

class DownloadProgressScreen(Screen):
    BINDINGS = [Binding("escape", "pop", "Close")]

    def __init__(self, chapters: list, slug: str, source=None):
        super().__init__()
        self.chapters = chapters
        self.slug = slug
        self._done = False
        self.source = source or _get_source(slug)
 
    def compose(self):
        yield Header(show_clock=False)
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
            async with sem:
                return await src.save_chapter(ch["url"], ch["title"], self.slug)

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

class LanguagePicker(Screen):
    BINDINGS = [Binding("escape", "dismiss_pop", "Back")]

    def compose(self):
        yield Header(show_clock=False)
        yield Static("Target Language", classes="title")
        with ScrollableContainer():
            yield ListView(*[ListItem(Label(name)) for name in LANGUAGES])
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected):
        code = list(LANGUAGES.values())[event.list_view.index]
        self.dismiss(code)

    def on_mount(self):
        try:
            self.query_one(ListView).focus()
        except Exception:
            pass

    def action_dismiss_pop(self):
        self.dismiss(None)


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
        yield Header(show_clock=False)
        yield Static(id="chapter-header")
        with ScrollableContainer():
            yield Static(id="chapter-text")
        yield Footer()
    async def on_mount(self):
        await self.load_chapter()


    async def load_chapter(self):
        assert self.source is not None
        ch = self.chapters[self.current]
        lines = await self.source.read_chapter(ch["url"])
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
        _mark_seen(self.slug, self.current)

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
    async def action_download(self):
        assert self.source is not None
        ch = self.chapters[self.current]
        ok = await self.source.save_chapter(ch["url"], ch["title"], self.slug)
        self.notify("Downloaded!" if ok else "Already saved.", timeout=2)
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
        asyncio.create_task(self._do_translate(lang))

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




class NovelFetchApp(App):
    CSS = """
    Screen {
        background: $surface;
    }
    .title {
        text-align: center;
        text-style: bold;
        color: $accent;
        padding: 0 1;
    }
    .banner {
        text-align: center;
        color: $accent;
        padding: 2 1 0 1;
    }
    #chapter-text, #local-text {
        margin: 0 1;
    }
    #chapter-text.rtl, #local-text.rtl {
        text-align: right;
    }
    #chapter-header {
        text-align: center;
        color: $accent;
        text-style: bold;
        padding: 0 1;
    }
    RadioSet {
        margin: 0 1;
        background: transparent;
        border: none;
    }
    RadioSet:focus {
        border: none;
    }
    RadioSet > RadioButton > .toggle--button,
    RadioSet > RadioButton.-on > .toggle--button {
        color: transparent;
        background: transparent;
    }
    RadioSet > RadioButton.-selected > .toggle--label {
        background: transparent;
        color: $accent;
        text-style: bold underline;
    }
    ListView {
        margin: 0 1;
    }
    ListItem {
        padding: 0 1;
    }
    .loading {
        display: none;
        height: 3;
        content-align: center middle;
    }
    .loading.-visible {
        display: block;
    }
    #dl-bar {
        margin: 1 2;
    }
    #dl-status {
        margin: 0 2;
        text-style: italic;
        color: $text-muted;
    }
    #dl-novel {
        text-align: center;
        color: $text-muted;
        padding: 0 1;
    }
    Input {
        margin: 0 1;
    }
    #page-info {
        padding: 0 1;
        text-style: italic;
        color: $text-muted;
    }
    """
    def __init__(self):
        super().__init__()
        self.current_source = None

    def on_mount(self):
        self.push_screen(MainMenu())


if __name__=="__main__":
    NovelFetchApp().run()
