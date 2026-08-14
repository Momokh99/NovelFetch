import asyncio
import os

from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.toolbar import MDTopAppBar

from progress import LANGUAGES, progress
from async_runner import async_loop
from translation import _translate_text


def _chapter_sort_key(fname):
    import re
    nums = re.findall(r"\d+", fname)
    return int(nums[0]) if nums else 0


def _local_chapters(slug):
    """Build a chapter list from the downloaded novels/{slug}/*.txt files."""
    chap_dir = os.path.join("novels", slug)
    if not os.path.isdir(chap_dir):
        return []
    files = [f for f in os.listdir(chap_dir) if f.endswith(".txt")]
    files.sort(key=_chapter_sort_key)
    chapters = []
    for i, f in enumerate(files, 1):
        title = os.path.basename(f).replace(".txt", "").replace("_", " ").title()
        chapters.append({"num": i, "title": title, "url": ""})
    return chapters


class ReaderScreen(MDScreen):
    """Read chapters local-first (downloaded files), falling back to the
    source's read_chapter() over the network. Prev/next, translate/revert,
    and A-/A+ font size controls."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chapters = []
        self.slug = ""
        self.source = None
        self.current = 0
        self._original_text = ""
        self._translated_text = ""
        self._lang = None
        self._font_size = 16
        self._busy = False
        self._lang_dialog = None

        self.topbar = MDTopAppBar(
            title="Reader",
            left_action_items=[["arrow-left", lambda *_: self._back()]],
            right_action_items=self._toolbar_actions(),
        )
        self.add_widget(self.topbar)

        self.scroll = ScrollView()
        self.body_label = MDLabel(
            text="",
            size_hint_y=None,
            adaptive_height=True,
            padding=("16dp", "16dp"),
            font_size=self._font_size,
        )
        self.body_label.bind(width=lambda *_: self._reflow())
        self.scroll.add_widget(self.body_label)
        self.add_widget(self.scroll)

        self.prev_btn = MDIconButton(icon="skip-previous", on_release=lambda *_: self._prev())
        self.next_btn = MDIconButton(icon="skip-next", on_release=lambda *_: self._next())
        self.counter = MDLabel(text="", halign="center", theme_text_color="Secondary")

        bottom = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None, height="56dp",
            padding="8dp", spacing="8dp",
        )
        bottom.add_widget(self.prev_btn)
        bottom.add_widget(self.counter)
        bottom.add_widget(self.next_btn)
        self.add_widget(bottom)

    # ---------- toolbar ----------

    def _toolbar_actions(self):
        items = [
            ["format-font-size-decrease", lambda *_: self._font(-2)],
            ["format-font-size-increase", lambda *_: self._font(2)],
        ]
        if self._translated_text:
            items.insert(0, ["undo-variant", lambda *_: self._revert()])
        else:
            items.insert(0, ["translate", lambda *_: self._pick_language()])
        return items

    def _refresh_toolbar(self):
        self.topbar.right_action_items = self._toolbar_actions()

    # ---------- goto() contract ----------

    def load(self, chapters=None, slug="", source=None, title="Reader", start=0, **kwargs):
        self.slug = slug
        self.source = source
        self.chapters = chapters if chapters is not None else _local_chapters(slug)
        if not self.chapters:
            self._notify("No chapters to read.")
            Clock.schedule_once(lambda dt: MDApp.get_running_app().back(), 0.3)
            return
        start = max(0, min(start, len(self.chapters) - 1))
        self._load_chapter(start)

    # ---------- loading ----------

    def _load_chapter(self, idx):
        if not (0 <= idx < len(self.chapters)) or self._busy:
            return
        self.current = idx
        self._original_text = ""
        self._translated_text = ""
        self._lang = None
        self._refresh_toolbar()
        self._set_busy(True)
        self.topbar.title = self.chapters[idx]["title"]
        self.counter.text = f"{idx + 1}/{len(self.chapters)}"

        ch = self.chapters[idx]
        safe_title = ch["title"].replace("/", "-").replace(" ", "_") + ".txt"
        local_path = os.path.join("novels", self.slug, safe_title) if self.slug else None

        if local_path and os.path.exists(local_path):
            try:
                with open(local_path, encoding="utf-8") as f:
                    content = f.read()
                self._set_busy(False)
                self._original_text = content
                self._show_text(content)
                progress.mark_seen(self.slug, idx)
            except Exception:
                self._set_busy(False)
                self._notify("Could not read chapter.")
            return

        if self.source is None or not ch.get("url"):
            self._set_busy(False)
            self._notify("No source for this chapter.")
            return

        async def coro():
            return await self.source.read_chapter(ch["url"])

        async_loop.run(coro(), self._on_chapter_loaded)

    def _on_chapter_loaded(self, lines, error):
        self._set_busy(False)
        if error is not None or not lines:
            self._notify("Failed to load chapter. Check your connection.")
            return
        self._original_text = "\n\n".join(lines)
        self._show_text(self._original_text)
        progress.mark_seen(self.slug, self.current)

    def _show_text(self, text):
        self.body_label.text = text
        self.body_label.halign = "left"
        self.body_label.text_language = ""
        self.scroll.scroll_y = 1
        Clock.schedule_once(lambda dt: self._reflow(), 0)

    def _reflow(self):
        w = self.body_label.width
        if w > 0:
            self.body_label.text_size = (w, None)

    # ---------- navigation ----------

    def _next(self):
        if self.current < len(self.chapters) - 1:
            self._load_chapter(self.current + 1)

    def _prev(self):
        if self.current > 0:
            self._load_chapter(self.current - 1)

    def _set_busy(self, busy):
        self._busy = busy
        self.prev_btn.disabled = busy or self.current == 0
        self.next_btn.disabled = busy or self.current == len(self.chapters) - 1

    # ---------- translation ----------

    def _pick_language(self):
        if self._busy or not self._original_text:
            return
        rows = MDList()
        for label, code in LANGUAGES.items():
            rows.add_widget(OneLineListItem(
                text=label, on_release=lambda *_, c=code: self._start_translate(c)))
        self._lang_dialog = MDDialog(title="Translate to", type="custom", content_cls=rows)
        self._lang_dialog.open()

    def _start_translate(self, code):
        if self._lang_dialog is not None:
            self._lang_dialog.dismiss()
        if self._busy or not self._original_text:
            return
        self._set_busy(True)

        async def coro():
            return await asyncio.to_thread(_translate_text, self._original_text, code)

        async_loop.run(coro(), lambda res, err, c=code: self._on_translated(res, err, c))

    def _on_translated(self, translated, error, code):
        self._set_busy(False)
        if error is not None or not translated:
            self._notify("Translation failed. Check your internet.")
            return
        self._translated_text = translated
        self._lang = code
        self.body_label.text = translated
        if code == "ar":
            self.body_label.halign = "right"
            self.body_label.text_language = "ar"
        else:
            self.body_label.halign = "left"
            self.body_label.text_language = ""
        self._refresh_toolbar()
        self.scroll.scroll_y = 1
        Clock.schedule_once(lambda dt: self._reflow(), 0)

    def _revert(self):
        if not self._translated_text:
            return
        self._translated_text = ""
        self._lang = None
        self._show_text(self._original_text)
        self._refresh_toolbar()

    # ---------- font size ----------

    def _font(self, delta):
        self._font_size = min(28, max(14, self._font_size + delta))
        self.body_label.font_size = self._font_size
        Clock.schedule_once(lambda dt: self._reflow(), 0)

    # ---------- misc ----------

    def _back(self):
        progress.flush()   # persist read marks before leaving
        MDApp.get_running_app().back()

    def _notify(self, text):
        MDSnackbar(MDLabel(text=text)).open()
