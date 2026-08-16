from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar

from async_runner import async_loop
from screens import utils
from screens.topbar import TopBar


class DownloadProgressScreen(MDScreen):
    """Downloads a set of chapters with a live progress bar, then pops back.

    Started via goto("download_progress", ...) — goto() hands data to load().
    progress_cb runs on the async loop thread, so every update hops back to
    the Kivy thread via Clock.schedule_once before touching widgets."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chapters = []
        self.slug = ""
        self.source = None
        self._title = ""
        self._total = 0
        self._done = False

        self.topbar = TopBar(title="Downloading…", back=True, on_back=self._back)

        box = MDBoxLayout(
            orientation="vertical",
            padding="24dp",
            spacing="16dp",
            adaptive_height=True,
        )
        self.title_label = MDLabel(
            text="", bold=True, font_style="Subtitle1", adaptive_height=True)
        self.progress_bar = MDProgressBar(value=0, max=1)
        self.status_label = MDLabel(
            text="", theme_text_color="Secondary", adaptive_height=True)

        box.add_widget(self.title_label)
        box.add_widget(self.progress_bar)
        box.add_widget(self.status_label)
        root = MDBoxLayout(orientation="vertical")
        root.add_widget(self.topbar)
        root.add_widget(box)
        self.add_widget(root)

    def load(self, chapters=None, slug="", source=None, title="", total=None, **kwargs):
        self.chapters = chapters or []
        self.slug = slug
        self.source = source
        self._title = title or "Downloading…"
        self._total = total or len(self.chapters)
        self.topbar.set_title(self._title)
        self.title_label.text = self._title
        self.progress_bar.max = max(len(self.chapters), 1)
        self.progress_bar.value = 0
        self.status_label.text = f"0/{len(self.chapters)} — 0 saved"
        self._done = False
        Clock.schedule_once(lambda dt: self._start(), 0)

    def _start(self):
        if self._done or not self.chapters:
            if not self.chapters:
                self._notify("No chapters to download.")
                MDApp.get_running_app().back()
            return
        if self.source is None:
            self._notify("No source for this novel.")
            MDApp.get_running_app().back()
            return

        async def coro():
            return await utils._download_novel(
                self.source, self.slug, self.chapters, self._title,
                total=self._total, progress_cb=self._on_progress)

        async_loop.run(coro(), self._on_done)

    def _on_progress(self, done, saved):
        # Runs on the async loop thread — hop to Kivy thread before UI updates.
        Clock.schedule_once(
            lambda dt: self._set_progress(done, saved))

    def _set_progress(self, done, saved):
        self.progress_bar.value = min(done, self.progress_bar.max)
        self.status_label.text = f"{done}/{len(self.chapters)} — {saved} saved"

    def _on_done(self, result, error):
        self._done = True
        if error is not None:
            self._notify("Download failed.")
        else:
            saved, failed = result
            if saved:
                self._notify(f"Saved {saved} chapters to library.")
            elif failed:
                self._notify("Download failed. Check your connection.")
            else:
                self._notify("Novel is already in the library.")
        MDApp.get_running_app().root.homescreen_library_refresh()
        MDApp.get_running_app().back()

    def _back(self):
        MDApp.get_running_app().back()

    def _notify(self, text):
        MDSnackbar(MDLabel(text=text)).open()
