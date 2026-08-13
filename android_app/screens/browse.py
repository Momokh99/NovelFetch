from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.snackbar import MDSnackbar

from async_runner import async_loop

BROWSE = {
    "hot": "Hot novels",
    "latest": "Latest releases",
    "popular": "Most popular",
    "completed": "Completed",
}

class BrowseSection(MDBoxLayout):
    """The discovery block shared by Home and Search: browse rows + genres."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", adaptive_height=True, **kwargs)
        self._busy = False
        self._genre_dialog = None

        self.browse_list = MDList()
        for key, label in BROWSE.items():
            # k=key freezes the loop variable (closure trap)
            self.browse_list.add_widget(OneLineListItem(
                text=label, on_release=lambda *_, k=key: self.browse(k)))
        self.browse_list.add_widget(OneLineListItem(
            text="Genres", on_release=lambda *_: self.open_genres()))
        self.add_widget(self.browse_list)

    # ---------- browse ----------

    def browse(self, key):
        if self._busy:
            return
        source = MDApp.get_running_app().current_source
        if source is None:
            self._notify("No source selected.")
            return

        async def coro():
            soup = await source.fetch_url(source.browse_urls[key])
            return source.extract_novel_rows(soup)

        self._set_busy(True)
        async_loop.run(coro(), lambda res, err, k=key: self._on_done(res, err, BROWSE[k]))

    # ---------- genres ----------


    def open_genres(self):
        if self._busy:
            return
        source = MDApp.get_running_app().current_source
        if source is None:
            self._notify("No source selected.")
            return

        rows = MDList()
        for slug, label in source.genres.items():
            rows.add_widget(OneLineListItem(
                text=label, on_release=lambda *_, g=slug: self.browse_genre(g)))
        # Instance ref: a dialog with no strong ref can be GC'd mid-open.
        self._genre_dialog = MDDialog(title="Genres", type="custom", content_cls=rows)
        self._genre_dialog.open()

    def browse_genre(self, genre_slug):
        if self._genre_dialog is not None:
            self._genre_dialog.dismiss()
        if self._busy:
            return
        source = MDApp.get_running_app().current_source

        async def coro():
            return await source.browse_genre(genre_slug)

        self._set_busy(True)
        async_loop.run(coro(), lambda res, err: self._on_done(res, err, "Genres"))

# ---------- result routing ----------

    def _on_done(self, novels, error, title):
        self._set_busy(False)
        if error is not None:
            self._notify("Failed to fetch novels. Check your connection.")
        elif not novels:
            self._notify("No novels found.")
        else:
            MDApp.get_running_app().goto(
                "novel_list",
                novels=novels,
                source=MDApp.get_running_app().current_source,
                title=title,
            )

    # ---------- helpers ----------

    def _set_busy(self, busy):
        self._busy = busy
        self.browse_list.disabled = busy   # rows ignore taps while fetching

    def _notify(self, text):
        MDSnackbar(text=text).open()



