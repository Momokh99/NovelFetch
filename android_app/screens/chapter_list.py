from kivy.clock import Clock
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


class ChapterListScreen(MDScreen):
    """Chapters of one novel, with read ✓ marks and a Continue shortcut.
    Reading itself is the Phase 3 reader screen; taps are placeholders for now."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chapters = []
        self.slug = ""
        self.source = None

        self.topbar = MDTopAppBar(
            title="Chapter list",
            left_action_items=[["arrow-left", lambda *_: self._back()]],
        )
        self.add_widget(self.topbar)

        header = MDBoxLayout(orientation="vertical", adaptive_height=True, padding="16dp")
        self.info_label = MDLabel(text="", adaptive_height=True)
        self.continue_btn = MDRaisedButton(
            text="Continue",
            size_hint=(1, None),
            height="48dp",
            md_bg_color=[0.2, 0.5, 0.9, 1],
        )
        self.continue_btn.bind(on_release=lambda *_: self._notify("Reader in Phase 3"))
        header.add_widget(self.info_label)
        header.add_widget(self.continue_btn)

        body = ScrollView()
        content = MDBoxLayout(orientation="vertical", adaptive_height=True)
        content.add_widget(header)
        self.list_view = MDList()
        content.add_widget(self.list_view)
        body.add_widget(content)

        self.add_widget(body)
        self._rebuild()

    def load(self, chapters, slug="", source=None, title="Chapter list"):
        # goto() contract: stash fresh data, then redraw.
        self.chapters = chapters
        self.slug = slug
        self.source = source
        self.topbar.title = title
        self._rebuild()

    def _rebuild(self):
        self.info_label.text = f"Chapters: 1-{len(self.chapters)}"
        self.list_view.clear_widgets()

        # ✓ marks come from the shared ProgressTracker via the qualified slug.
        seen = progress.get_seen(self.slug) if self.slug else set()
        last = progress.get_last(self.slug)
        self.continue_btn.opacity = 1 if last is not None else 0
        self.continue_btn.disabled = last is None

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

    def _back(self):
        MDApp.get_running_app().goto("tabs")

    def _notify(self, text):
        MDSnackbar(text=text).open()