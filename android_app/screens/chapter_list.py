from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.image import AsyncImage
from kivy.uix.scrollview import ScrollView

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.toolbar import MDTopAppBar

from progress import progress
from async_runner import async_loop
from screens import utils


class ChapterListScreen(MDScreen):
    """Chapters of one novel, with read ✓ marks and a Continue shortcut.
    Reading itself is the Phase 3 reader screen; taps are placeholders for now."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chapters = []
        self.slug = ""
        self.source = None
        self._busy = False
        self._base_info = ""
        self._cover = ""
        self._pending_idx = None
        self._novel_title = ""

        self.topbar = MDTopAppBar(
            title="Chapter list",
            left_action_items=[["arrow-left", lambda *_: self._back()]],
            right_action_items=[["download", lambda *_: self._download_all()]],
        )
        self.add_widget(self.topbar)

        header = MDBoxLayout(
            orientation="horizontal", adaptive_height=False,
            padding="16dp", spacing="16dp",
            size_hint_y=None, height="120dp",
        )
        texts = MDBoxLayout(orientation="vertical", size_hint_y=1, spacing="2dp")
        self.title_label = MDLabel(
            text="", bold=True, font_style="Subtitle1",
            size_hint_y=None, height="28dp")
        self.info_label = MDLabel(
            text="", theme_text_color="Secondary",
            font_style="Caption", size_hint_y=None, height="20dp")
        texts.add_widget(self.title_label)
        texts.add_widget(self.info_label)

        self.cover_img = AsyncImage(
            source="",
            size_hint=(None, 1),
            width=dp(90),
            keep_ratio=True,
            allow_stretch=True,
        )
        header.add_widget(texts)
        header.add_widget(self.cover_img)

        self.continue_btn = MDRaisedButton(
            text="Continue",
            size_hint=(1, None),
            height="48dp",
            md_bg_color=[0.2, 0.5, 0.9, 1],
        )
        self.continue_btn.bind(on_release=lambda *_: self._notify("Reader in Phase 3"))

        body = ScrollView()
        content = MDBoxLayout(orientation="vertical", adaptive_height=True)
        content.add_widget(header)
        content.add_widget(self.continue_btn)
        self.list_view = MDList()
        content.add_widget(self.list_view)
        body.add_widget(content)

        self.add_widget(body)
        self._rebuild()

    def load(self, chapters, slug="", source=None, title="Chapter list", cover=""):
        # goto() contract: stash fresh data, then redraw.
        self.chapters = chapters
        self.slug = slug
        self.source = source
        self._cover = cover or ""
        self._novel_title = title
        self._rebuild()

    def _rebuild(self):
        self._base_info = f"Chapters: 1-{len(self.chapters)}"
        self.title_label.text = self._novel_title
        self.info_label.text = self._base_info
        self.cover_img.source = self._cover
        self.cover_img.opacity = 1 if self._cover else 0
        self.list_view.clear_widgets()

        # ✓ marks come from the shared ProgressTracker via the qualified slug.
        seen = progress.get_seen(self.slug) if self.slug else set()
        last = progress.get_last(self.slug)
        # Collapse the Continue button to zero height instead of leaving a
        # 48dp dead gap when there's nothing to continue yet.
        self.continue_btn.opacity = 1 if last is not None else 0
        self.continue_btn.disabled = last is None
        self.continue_btn.height = "48dp" if last is not None else 0

        for i, ch in enumerate(self.chapters):
            prefix = "✓ " if i in seen else "  "
            item = OneLineListItem(
                text=prefix + ch["title"],
                on_release=lambda *_, idx=i: self._open(idx),
            )
            self.list_view.add_widget(item)

        # Fresh chapter data may arrive while the widget is already mounted
        # (re-navigating with new data); reflow height for the new rows.
        Clock.schedule_once(lambda dt: self.info_label.parent._trigger_layout(), 0)

    def _open(self, idx):
        # Reader screen lands in Phase 3; folder the index now.
        self._pending_idx = idx
        self._notify("Reader screen in Phase 3")

    def _download_all(self):
        if self._busy or not self.source or not self.slug:
            return
        self._busy = True
        self.info_label.text = "Downloading…"

        async def coro():
            return await utils._download_novel(
                self.source, self.slug, self.chapters, self._novel_title)

        async_loop.run(coro(), self._on_download_done)

    def _on_download_done(self, result, error):
        self._busy = False
        if error is not None:
            self.info_label.text = self._base_info
            self._notify("Download failed.")
            return
        saved, failed = result
        self.info_label.text = self._base_info
        if saved:
            self._notify(f"Saved {saved} chapters to library.")
            MDApp.get_running_app().root.homescreen_library_refresh()
        elif failed:
            self._notify("Download failed. Check your connection.")
        else:
            self._notify("Novel is already in the library.")

    def _back(self):
        MDApp.get_running_app().back()

    def _notify(self, text):
        MDSnackbar(text=text).open()