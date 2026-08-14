from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.image import AsyncImage
from kivy.uix.scrollview import ScrollView

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import (
    MDList,
    OneLineAvatarIconListItem,
    OneLineListItem,
    CheckboxLeftWidget,
)
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.toolbar import MDTopAppBar

from progress import progress
from async_runner import async_loop
from screens import utils


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

        self.topbar = MDTopAppBar(
            title="Chapter list",
            left_action_items=[["arrow-left", lambda *_: self._left_action()]],
            right_action_items=[
                ["select-multiple", lambda *_: self._toggle_select_mode()],
                ["dots-vertical", lambda *_: self._open_overflow()],
            ],
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
        self.continue_btn.bind(on_release=lambda *_: self._continue())

        self.download_btn = MDRaisedButton(
            text="Download selected",
            size_hint=(1, None),
            height="48dp",
            md_bg_color=[0.2, 0.5, 0.9, 1],
        )
        self.download_btn.bind(on_release=lambda *_: self._download_selected())

        body = ScrollView()
        content = MDBoxLayout(orientation="vertical", adaptive_height=True)
        content.add_widget(header)
        content.add_widget(self.continue_btn)
        content.add_widget(self.download_btn)
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

        for i, ch in enumerate(self.chapters):
            prefix = "✓ " if i in seen else "  "
            if self._select_mode:
                item = OneLineAvatarIconListItem(
                    text=prefix + ch["title"],
                    on_release=lambda *_, idx=i: self._toggle_selection(idx),
                )
                cbx = CheckboxLeftWidget(active=i in self._selected)
                cbx.bind(on_active=lambda w, val, idx=i: self._toggle_selection(idx, active=val))
                item.add_widget(cbx)
            else:
                item = OneLineListItem(
                    text=prefix + ch["title"],
                    on_release=lambda *_, idx=i: self._open(idx),
                )
            self.list_view.add_widget(item)

        # Fresh chapter data may arrive while the widget is already mounted
        # (re-navigating with new data); reflow height for the new rows.
        Clock.schedule_once(lambda dt: self.info_label.parent._trigger_layout(), 0)

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
        for i, w in enumerate(self.list_view.children):
            cbx = w.children[0] if w.children else None
            if isinstance(cbx, CheckboxLeftWidget):
                index = len(self.chapters) - 1 - i
                if cbx.active != (index in self._selected):
                    cbx.active = index in self._selected

    def _update_download_button(self):
        n = len(self._selected)
        self.download_btn.opacity = 1 if (self._select_mode and n) else 0
        self.download_btn.disabled = not (self._select_mode and n)
        self.download_btn.height = "48dp" if (self._select_mode and n) else 0
        if n:
            self.download_btn.text = f"Download selected ({n})"

    # ---------- overflow menu ----------

    def _open_overflow(self):
        rows = MDList()
        rows.add_widget(OneLineListItem(
            text="Download all",
            on_release=lambda *_: self._download_subset(self.chapters),
        ))
        # Instance ref: a dialog with no strong ref can be GC'd mid-open.
        self._overflow = MDDialog(title="Options", type="custom", content_cls=rows)
        self._overflow.open()

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