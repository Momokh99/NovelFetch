import os
import shutil

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.image import AsyncImage
from kivy.uix.scrollview import ScrollView

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.toolbar import MDTopAppBar

from async_runner import async_loop          # Phase 0 bridge: UI never blocks
from progress import _scan_library, _slug_to_title, progress
from epub import _export_epub
from screens import utils                    # _get_source helper, meta
from screens.novel_list import _TapCard
from screens.source_picker import open_source_picker


class HomeTab(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.topbar = MDTopAppBar(
            title="NovelFetch",
            right_action_items=[["book-open-variant", lambda *_: open_source_picker()]],
        )
        self.add_widget(self.topbar)

        body = ScrollView()
        content = MDBoxLayout(orientation="vertical", adaptive_height=True,
                              padding="16dp", spacing="8dp")

        content.add_widget(MDLabel(text="My Library", bold=True, adaptive_height=True))
        self.library_list = MDList()
        content.add_widget(self.library_list)

        body.add_widget(content)
        self.add_widget(body)

        # current_source is set in App.on_start(), AFTER build(). A zero-delay
        # Clock callback fires on the first frame — after on_start has run.
        Clock.schedule_once(lambda dt: self.refresh_library(), 0)

    # ---------- library ----------

    def refresh_library(self):
        # _scan_library() walks novels/ synchronously — cheap, thread-safe.
        novels = _scan_library()
        self.library_list.clear_widgets()
        for n in novels:
            meta = utils._read_meta(n["slug"])   # {"title", "cover", "chapters"} or {}
            title = meta.get("title") or n["title"]
            last = progress.get_last(n["slug"])    # stored chapter index or None
            count = meta.get("chapters") or n["count"]
            sub = f"{count} chapters"
            if last is not None:
                sub += f" · Last: Ch. {last + 1}"  # +1: index -> human number

            row = _TapCard(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(120),
                padding="12dp",
                spacing="16dp",
            )
            cover = os.path.join("novels", n["slug"], meta["cover"]) if meta.get("cover") else ""
            img = AsyncImage(
                source=cover,
                size_hint=(None, 1),
                width=dp(70),
                keep_ratio=True,
                allow_stretch=True,
            )
            texts = MDBoxLayout(orientation="vertical", size_hint_y=1, spacing="2dp")
            texts.add_widget(MDLabel(
                text=title, bold=True,
                font_style="Subtitle1", size_hint_y=None, height="28dp"))
            texts.add_widget(MDLabel(
                text=sub, theme_text_color="Secondary",
                font_style="Caption", size_hint_y=None, height="20dp"))
            row.add_widget(img)
            row.add_widget(texts)
            row.on_release = lambda *_, nv=n, t=title: self.library_menu(nv, t)
            self.library_list.add_widget(row)

    # ---------- library actions ----------

    def library_menu(self, novel, title=None):
        # Tap a library row -> actions. Phase 3 adds "Read" here.
        slug = novel["slug"]
        dialog = MDDialog(
            title=title or novel["title"],
            buttons=[
                MDFlatButton(text="Delete",
                             on_release=lambda *_: self._delete(slug, dialog)),
                MDFlatButton(text="Export EPUB",
                             on_release=lambda *_: self._export(slug, dialog)),
            ],
        )
        dialog.open()

    def _export(self, slug, dialog):
        dialog.dismiss()
        source = utils._get_source(slug)       # slug -> Source via registry
        if source is None:
            self._notify("No source for this novel.")
            return

        async def coro():
            return await _export_epub(slug, source)  # fetches cover, writes epub

        async_loop.run(coro(), self._on_export_done)

    def _on_export_done(self, path, error):
        if error is not None:
            self._notify("Export failed.")
        elif path:
            self._notify(f"Exported: {path}")
        else:
            self._notify("No chapters to export.")

    def _delete(self, slug, dialog):
        dialog.dismiss()
        # Two-step confirm: mobile has no "press x twice", so explicit dialog.
        confirm = MDDialog(
            title=f"Delete {_slug_to_title(slug)}?",
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda *_: confirm.dismiss()),
                MDFlatButton(text="Delete",
                             on_release=lambda *_: self._do_delete(slug, confirm)),
            ],
        )
        confirm.open()

    def _do_delete(self, slug, dialog):
        dialog.dismiss()
        try:
            shutil.rmtree(os.path.join("novels", slug))  # relative -> chdir-safe
            progress.remove(slug)   # drop stale read marks for this novel
            progress.flush()
        except Exception:
            self._notify("Delete failed.")
            return
        self.refresh_library()
        self._notify(f"Deleted {_slug_to_title(slug)}")

    # ---------- helpers ----------

    def _notify(self, text):
        MDSnackbar(text=text).open()