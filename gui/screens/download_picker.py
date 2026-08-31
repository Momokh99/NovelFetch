from kivymd.app import MDApp
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogContentContainer,
    MDDialogHeadlineText,
)
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, MDListItem, MDListItemHeadlineText
from kivymd.uix.screen import MDScreen

from core.progress import LANGUAGES, progress
from gui.screens import utils
from gui.screens.utils import _snack

_CODE_TO_LABEL = {v: k for k, v in LANGUAGES.items()}


class DownloadPickerScreen(MDScreen):
    """Mini-screen for choosing which chapters to download.  Two sections:
    Original (English) and Translated — each offering next 5/10/25, unread,
    and all.  A language selector row at the top controls the target
    language for translated downloads.

    Launched from ChapterListScreen via goto("download_picker", ...)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chapters = []
        self.slug = ""
        self.source = None
        self._title = ""
        self._total = 0
        self._lang_code = "ar"
        self._lang_dialog = None

        self.topbar = self.ids.topbar
        self.title_label = self.ids.title_label
        self.summary_label = self.ids.summary_label
        self.lang_label = self.ids.lang_label
        self.list_view = self.ids.list_view

    def load(self, chapters=None, slug="", source=None, title="",
             total=None, **kwargs):
        self.chapters = chapters or []
        self.slug = slug
        self.source = source
        self._title = title or "Download"
        self._total = total or len(self.chapters)
        self.topbar.set_title(self._title)
        self.title_label.text = self._title
        self._lang_label_update()
        self._rebuild()

    def _lang_label_update(self):
        self.lang_label.text = _CODE_TO_LABEL.get(self._lang_code,
                                                    self._lang_code)

    def _rebuild(self):
        self.list_view.clear_widgets()
        local = utils._local_chapters(self.slug) if self.slug else []
        downloaded = len(local)
        seen = progress.get_seen(self.slug) if self.slug else set()
        unread = [ch for i, ch in enumerate(self.chapters)
                  if i not in seen and i >= downloaded]
        remaining = self.chapters[downloaded:]
        self.summary_label.text = (
            f"{downloaded} downloaded  |  {len(unread)} unread  |  "
            f"{len(self.chapters)} total"
        )

        # --- Original (English) ---
        if remaining:
            self.list_view.add_widget(self._section_header("Original"))
            for n in (5, 10, 25):
                subset = remaining[:n]
                self.list_view.add_widget(MDListItem(MDListItemHeadlineText(
                    text=f"Next {len(subset)}",
                ), on_release=lambda *_, s=subset: self._go(s)))
            if unread:
                self.list_view.add_widget(MDListItem(MDListItemHeadlineText(
                    text=f"All unread ({len(unread)})",
                ), on_release=lambda *_, s=unread: self._go(s)))
            if self.chapters:
                self.list_view.add_widget(MDListItem(MDListItemHeadlineText(
                    text=f"All ({len(self.chapters)})",
                ), on_release=lambda *_, s=self.chapters: self._go(s)))

        # --- Translated ---
        if self.chapters:
            lang_label = _CODE_TO_LABEL.get(self._lang_code, self._lang_code)
            self.list_view.add_widget(self._section_header(
                f"Translated ({lang_label})"))
            for n in (5, 10, 25):
                subset = remaining[:n] if remaining else []
                if subset:
                    self.list_view.add_widget(MDListItem(MDListItemHeadlineText(
                        text=f"Next {len(subset)}",
                    ), on_release=lambda *_, s=subset: self._go_tr(s)))
            if unread:
                self.list_view.add_widget(MDListItem(MDListItemHeadlineText(
                    text=f"All unread ({len(unread)})",
                ), on_release=lambda *_, s=unread: self._go_tr(s)))
            if self.chapters:
                self.list_view.add_widget(MDListItem(MDListItemHeadlineText(
                    text=f"All ({len(self.chapters)})",
                ), on_release=lambda *_, s=self.chapters: self._go_tr(s)))

    @staticmethod
    def _section_header(text):
        from kivy.metrics import dp
        from kivymd.uix.boxlayout import MDBoxLayout
        box = MDBoxLayout(
            size_hint_y=None, height=dp(32),
            padding=(dp(16), dp(12), dp(16), 0))
        box.add_widget(MDLabel(
            text=text, bold=True, theme_text_color="Secondary",
            font_style="Label", role="medium"))
        return box

    def _go(self, subset):
        MDApp.get_running_app().goto(
            "download_progress",
            chapters=subset,
            slug=self.slug,
            source=self.source,
            title=self._title,
            total=self._total,
        )

    def _go_tr(self, subset):
        MDApp.get_running_app().goto(
            "download_progress",
            chapters=subset,
            slug=self.slug,
            source=self.source,
            title=self._title,
            total=self._total,
            translate=True,
            lang=self._lang_code,
        )

    def _pick_language(self):
        rows = MDList()
        for label, code in LANGUAGES.items():
            rows.add_widget(MDListItem(MDListItemHeadlineText(
                text=label,
            ), on_release=lambda *_, c=code, l=label: self._set_lang(c, l)))
        self._lang_dialog = MDDialog(
            MDDialogHeadlineText(
                text="Translate to",
                halign="left",
            ),
            MDDialogContentContainer(rows),
        )
        self._lang_dialog.open()

    def _set_lang(self, code, label):
        if self._lang_dialog is not None:
            self._lang_dialog.dismiss()
        self._lang_code = code
        self._lang_label_update()
        self._rebuild()

    def _notify(self, text):
        _snack(text)
