from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

from gui.async_runner import async_loop
from gui.screens import utils
from gui.screens.utils import _snack


class DownloadProgressScreen(MDScreen):
    """Downloads a set of chapters with a live progress bar, then pops back.

    Started via goto("download_progress", ...) — goto() hands data to load().
    progress_cb runs on the async loop thread, so every update hops back to
    the Kivy thread via Clock.schedule_once before touching widgets.

    The widget tree lives in kv/download_dialog.kv; load() reaches the nodes
    through the ids aliased in __init__."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chapters = []
        self.slug = ""
        self.source = None
        self._title = ""
        self._total = 0
        self._done = False
        self._translate = False
        self._lang = ""
        self._future = None

        self.topbar = self.ids.topbar
        self.title_label = self.ids.title_label
        self.progress_bar = self.ids.progress_bar
        self.status_label = self.ids.status_label
        self.cancel_btn = self.ids.cancel_btn

    def load(self, chapters=None, slug="", source=None, title="",
             total=None, translate=False, lang="", **kwargs):
        self.chapters = chapters or []
        self.slug = slug
        self.source = source
        self._title = title or "Downloading…"
        self._total = total or len(self.chapters)
        self._translate = translate
        self._lang = lang
        self.topbar.set_title(self._title)
        self.title_label.text = self._title
        self.progress_bar.max = max(len(self.chapters), 1)
        self.progress_bar.value = 0
        self.status_label.text = f"0/{len(self.chapters)} — 0 saved"
        self._done = False
        self._future = None
        self.cancel_btn.opacity = 1
        self.cancel_btn.disabled = False
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
                total=self._total, progress_cb=self._on_progress,
                translate=self._translate, lang=self._lang)

        self._future = async_loop.run(coro(), self._on_done)

    def _on_progress(self, done, saved):
        # Runs on the async loop thread — hop to Kivy thread before UI updates.
        Clock.schedule_once(
            lambda dt: self._set_progress(done, saved))

    def _set_progress(self, done, saved):
        self.progress_bar.value = min(done, self.progress_bar.max)
        extra = " (translated)" if self._translate else ""
        self.status_label.text = f"{done}/{len(self.chapters)} — {saved} saved{extra}"

    def _on_done(self, result, error):
        if self.manager.current != "download_progress":
            return
        self._done = True
        self.cancel_btn.disabled = True
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

    def _cancel(self):
        if self._future is not None and not self._future.done():
            self._future.cancel()
        self._done = True
        self._notify("Download cancelled.")
        MDApp.get_running_app().back()

    def _notify(self, text):
        _snack(text)
