import os

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.image import AsyncImage

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import (
    MDList,
    OneLineAvatarIconListItem,
    OneLineListItem,
    CheckboxLeftWidget,
    IconLeftWidget,
)
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar

from progress import progress
from async_runner import async_loop
from screens import utils, theme


class ChapterListScreen(MDScreen):
    """Chapters of one novel, with read ✓ marks, a Continue shortcut, and
    selection-based downloading: enter select mode to check chapters, use the
    '…' menu for Download all."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chapters = []
        self.slug = ""
        self.source = None
        self._busy = False
        self._base_info = ""
        self._cover = ""
        self._novel_title = ""
        self._select_mode = False
        self._selected: set[int] = set()
        self._seen: set[int] = set()
        self._row_limit = 40
        self._row_step = 40
        self._built = 0
        self._loading_more = False

        self.topbar = self.ids.topbar
        self.topbar.on_back = self._left_action
        self._bookmark_disabled = False

        self.title_label = self.ids.title_label
        self.info_label = self.ids.info_label
        self.cover_img = self.ids.cover_img
        self.continue_btn = self.ids.continue_btn
        self.continue_btn.md_bg_color = theme.ACCENT
        self.continue_btn.bind(on_release=lambda *_: self._continue())
        self.download_btn = self.ids.download_btn
        self.download_btn.md_bg_color = theme.ACCENT
        self.download_btn.bind(on_release=lambda *_: self._download_selected())
        self._scroll_view = self.ids.scroll_view
        self._scroll_view.bind(scroll_y=self._on_scroll)
        self.list_view = self.ids.list_view
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

        # Build a set of indices for chapters that have a local file on disk.
        self._downloaded = set()
        if self.slug:
            chap_dir = os.path.join("novels", self.slug)
            if os.path.isdir(chap_dir):
                entries = set(os.listdir(chap_dir))
                meta_lang = utils._meta_lang(self.slug)
                for i, ch in enumerate(self.chapters):
                    safe = ch["title"].replace("/", "-").replace(" ", "_")
                    if (f"{safe}.txt" in entries
                            or (meta_lang
                                and f"{safe}_{meta_lang}.txt" in entries)):
                        self._downloaded.add(i)
            self.info_label.text = (
                self._base_info
                + f" · {len(self._downloaded)} downloaded")
        else:
            self.info_label.text = self._base_info
        if self._cover:
            utils.set_image_url(self.cover_img, self._cover)
            self.cover_img.opacity = 1
        else:
            self.cover_img.source = ""
            self.cover_img.opacity = 0
        self.list_view.clear_widgets()

        # ✓ marks come from the shared ProgressTracker via the qualified slug.
        seen = progress.get_seen(self.slug) if self.slug else set()
        self._seen = seen
        last = progress.get_last(self.slug)
        # Collapse the Continue button to zero height instead of leaving a
        # 48dp dead gap when there's nothing to continue yet. In select mode
        # both Continue and Download-selected are replaced by the selection UI.
        self.continue_btn.opacity = 1 if (last is not None and not self._select_mode) else 0
        self.continue_btn.disabled = last is None or self._select_mode
        self.continue_btn.height = "48dp" if (last is not None and not self._select_mode) else 0

        # Download-selected button: visible only in select mode with a selection.
        n = len(self._selected)
        self.download_btn.opacity = 1 if (self._select_mode and n) else 0
        self.download_btn.disabled = not (self._select_mode and n)
        self.download_btn.height = "48dp" if (self._select_mode and n) else 0
        if n:
            self.download_btn.text = f"Download selected ({n})"

        # Build topbar actions: bookmark (save novel) + select-multiple + overflow.
        # The bookmark icon shows registered vs not-yet-saved state.
        raw_slug = self.slug.split(":", 1)[-1] if self.slug else ""
        registered = bool(self.slug and utils._read_meta(self.slug))
        bookmark_icon = "bookmark" if registered else "bookmark-plus-outline"
        actions = [
            (bookmark_icon, self._save_novel),
            ("select-multiple", self._toggle_select_mode),
            ("dots-vertical", self._open_overflow),
        ]
        self.topbar.set_actions(actions)
        self._bookmark_disabled = registered

        for i, ch in enumerate(self.chapters[: self._row_limit]):
            self.list_view.add_widget(self._make_row(i, ch))
        self._built = len(self.chapters[: self._row_limit])
        self._loading_more = False

        # Fresh chapter data may arrive while the widget is already mounted
        # (re-navigating with new data); reflow height for the new rows.
        Clock.schedule_once(lambda dt: self.info_label.parent._trigger_layout(), 0)

    def _make_row(self, i, ch):
        """One chapter row; also stores its chapter index for checkbox sync."""
        seen = self._seen
        downloaded = self._downloaded
        if self._select_mode:
            prefix = "✓ " if i in seen else "  "
            item = OneLineAvatarIconListItem(
                text=prefix + ch["title"],
                on_release=lambda *_, idx=i: self._toggle_selection(idx),
            )
            cbx = CheckboxLeftWidget(active=i in self._selected)
            cbx.bind(on_active=lambda w, val, idx=i: self._toggle_selection(idx, active=val))
            item.add_widget(cbx)
        else:
            item = OneLineAvatarIconListItem(
                text=ch["title"],
                on_release=lambda *_, idx=i: self._open(idx),
            )
            if i in seen:
                item.add_widget(IconLeftWidget(
                    icon="check-circle", theme_text_color="Secondary"))
                item.theme_text_color = "Secondary"
            elif i in downloaded:
                item.add_widget(IconLeftWidget(
                    icon="download-circle", theme_text_color="Secondary"))
            else:
                item.add_widget(IconLeftWidget(icon="circle-outline"))
        item._idx = i
        return item

    def _on_scroll(self, instance, value):
        # Near the bottom: pull in the next chunk of chapter rows.
        if float(value) < 0.05:
            self._load_more()

    def _load_more(self, *args):
        # Called on scroll near the bottom: append the next chunk of rows so a
        # 500+-chapter novel is never built all at once on the main thread.
        if self._loading_more or self._built >= len(self.chapters):
            return
        self._loading_more = True
        end = min(self._built + self._row_step, len(self.chapters))
        for i, ch in enumerate(self.chapters[self._built:end], start=self._built):
            self.list_view.add_widget(self._make_row(i, ch))
        self._built = end
        self._loading_more = False

    def _open(self, idx):
        MDApp.get_running_app().goto(
            "reader",
            chapters=self.chapters,
            slug=self.slug,
            source=self.source,
            title=self._novel_title,
            start=idx,
        )

    def _continue(self):
        last = progress.get_last(self.slug)
        if last is not None:
            self._open(last)

    # ---------- selection mode ----------

    def _left_action(self):
        if self._select_mode:
            self._exit_select_mode()
        else:
            MDApp.get_running_app().back()

    def _toggle_select_mode(self):
        self._select_mode = not self._select_mode
        if not self._select_mode:
            self._selected.clear()
        self._rebuild()

    def _exit_select_mode(self):
        self._select_mode = False
        self._selected.clear()
        self._rebuild()

    def _toggle_selection(self, idx, active=None):
        # 'active' is None when toggled by a row tap (flip), else the checkbox's
        # own state (avoid flipping twice when a checkbox tap fires on_active).
        if active is None:
            if idx in self._selected:
                self._selected.discard(idx)
            else:
                self._selected.add(idx)
        else:
            if active:
                self._selected.add(idx)
            else:
                self._selected.discard(idx)
        self._sync_checkboxes()
        self._update_download_button()

    def _sync_checkboxes(self):
        # Sync every row's checkbox to _selected without re-triggering handlers.
        # KivyMD nests the CheckboxLeftWidget inside the row, so search the
        # subtree rather than assuming it is a direct child.
        def find_cbx(widget):
            for c in widget.children:
                if isinstance(c, CheckboxLeftWidget):
                    return c
                found = find_cbx(c)
                if found is not None:
                    return found
            return None

        for w in self.list_view.children:
            index = getattr(w, "_idx", None)
            if index is None:
                continue
            cbx = find_cbx(w)
            if cbx is not None and cbx.active != (index in self._selected):
                cbx.active = index in self._selected

    def _update_download_button(self):
        n = len(self._selected)
        self.download_btn.opacity = 1 if (self._select_mode and n) else 0
        self.download_btn.disabled = not (self._select_mode and n)
        self.download_btn.height = "48dp" if (self._select_mode and n) else 0
        if n:
            self.download_btn.text = f"Download selected ({n})"

    # ---------- overflow menu ----------

    def _save_novel(self):
        if self._bookmark_disabled:
            return
        if not self.source or not self.slug:
            return
        raw = self.slug.split(":", 1)[-1] if ":" in self.slug else self.slug
        if utils._read_meta(self.slug):
            MDSnackbar(MDLabel(text="Already in your library.")).open()
            return

        async def coro():
            return await utils._track_novel(
                self.source,
                {"slug": raw, "title": self._novel_title, "cover": self._cover})

        def on_done(result, error):
            if error is not None:
                MDSnackbar(MDLabel(text="Could not add. Check connection.")).open()
                return
            self._bookmark_disabled = True
            self.topbar.set_actions([
                ("bookmark", self._save_novel),
                ("select-multiple", self._toggle_select_mode),
                ("dots-vertical", self._open_overflow),
            ])
            MDSnackbar(MDLabel(text="Added to library.")).open()
            root = MDApp.get_running_app().root
            if hasattr(root, "homescreen_library_refresh"):
                root.homescreen_library_refresh()

        async_loop.run(coro(), on_done)

    def _open_overflow(self):
        dialog = getattr(self, "_overflow", None)
        if dialog is not None:
            dialog.dismiss()
        rows = MDList()
        if self.chapters:
            rows.add_widget(OneLineListItem(
                text="Download…",
                on_release=lambda *_: self._open_picker(),
            ))
        meta = utils._read_meta(self.slug) if self.slug else {}
        if meta:
            if meta.get("tracked") and not utils._has_chapters(self.slug):
                # Tracked-only: nothing downloaded yet -> Remove instead of Delete.
                rows.add_widget(OneLineListItem(
                    text="Remove from library",
                    on_release=lambda *_: self._remove_novel(),
                ))
            else:
                rows.add_widget(OneLineListItem(
                    text="Export EPUB",
                    on_release=lambda *_: self._export_epub(),
                ))
                rows.add_widget(OneLineListItem(
                    text="Delete",
                    on_release=lambda *_: self._delete_novel(),
                ))
        # Instance ref: a dialog with no strong ref can be GC'd mid-open.
        self._overflow = MDDialog(title="Options", type="custom", content_cls=rows)
        self._overflow.open()

    def _export_epub(self):
        dialog = getattr(self, "_overflow", None)
        if dialog is not None:
            dialog.dismiss()
        source = utils._get_source(self.slug)
        if source is None:
            self._notify("No source for this novel.")
            return

        async def coro():
            from epub import _export_epub
            return await _export_epub(self.slug, source)

        async_loop.run(coro(), self._on_export_done)

    def _on_export_done(self, path, error):
        if error is not None:
            self._notify("Export failed.")
        elif path:
            self._notify(f"Exported: {path}")
        else:
            self._notify("No chapters to export.")

    def _delete_novel(self):
        dialog = getattr(self, "_overflow", None)
        if dialog is not None:
            dialog.dismiss()
        confirm = MDDialog(
            title=f"Delete {self._novel_title}?",
            text="The files will be removed but the novel stays tracked, so "
                 "you can re-download it later from Updates.",
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda *_: confirm.dismiss()),
                MDFlatButton(text="Delete",
                             on_release=lambda *_: self._do_delete_novel(confirm, untrack=False)),
            ],
        )
        confirm.open()

    def _remove_novel(self):
        dialog = getattr(self, "_overflow", None)
        if dialog is not None:
            dialog.dismiss()
        confirm = MDDialog(
            title=f"Remove {self._novel_title} from library?",
            text="This removes the novel and its tracking entirely.",
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda *_: confirm.dismiss()),
                MDFlatButton(text="Remove",
                             on_release=lambda *_: self._do_delete_novel(confirm, untrack=True)),
            ],
        )
        confirm.open()

    def _do_delete_novel(self, dialog, untrack=False):
        dialog.dismiss()
        utils._delete_library(self.slug, untrack=untrack)
        root = MDApp.get_running_app().root
        if hasattr(root, "homescreen_library_refresh"):
            root.homescreen_library_refresh()
        MDApp.get_running_app().back()

    def _download_subset(self, subset):
        dialog = getattr(self, "_overflow", None)
        if dialog is not None:
            dialog.dismiss()
        if not subset or self._busy or not self.source or not self.slug:
            return
        MDApp.get_running_app().goto(
            "download_progress",
            chapters=subset,
            slug=self.slug,
            source=self.source,
            title=self._novel_title,
            total=len(self.chapters),
        )

    def _open_picker(self):
        dialog = getattr(self, "_overflow", None)
        if dialog is not None:
            dialog.dismiss()
        if not self.chapters or not self.source or not self.slug:
            return
        MDApp.get_running_app().goto(
            "download_picker",
            chapters=self.chapters,
            slug=self.slug,
            source=self.source,
            title=self._novel_title,
            total=len(self.chapters),
        )

    def _download_selected(self):
        subset = [ch for i, ch in enumerate(self.chapters) if i in self._selected]
        self._download_subset(subset)

    # ---------- legacy direct download ----------

    def _download_all(self):
        self._download_subset(self.chapters)

    def _back(self):
        MDApp.get_running_app().back()

    def _notify(self, text):
        MDSnackbar(MDLabel(text=text)).open()