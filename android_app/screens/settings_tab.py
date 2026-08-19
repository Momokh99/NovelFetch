import os
import shutil

from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, OneLineAvatarIconListItem, IconLeftWidget
from kivymd.uix.screen import MDScreen
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.snackbar import MDSnackbar

from progress import progress, _scan_library
from sources import REGISTRY
from screens.topbar import TopBar

PALETTES = [
    "Red", "Pink", "Purple", "DeepPurple", "Indigo", "Blue", "LightBlue",
    "Cyan", "Teal", "Green", "LightGreen", "Lime", "Yellow", "Amber",
    "Orange", "DeepOrange", "Brown", "Grey", "BlueGrey",
]


class SettingsTab(MDScreen):
    """Appearance (theme/palette) and library management."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._palette_dialog = None
        self._clear_dialog = None

        self.topbar = TopBar(title="Settings")

        body = ScrollView()
        content = MDBoxLayout(orientation="vertical", adaptive_height=True,
                              padding="16dp", spacing="8dp")

        # ---- appearance ----
        content.add_widget(MDLabel(
            text="Appearance", bold=True, adaptive_height=True))

        self.theme_row = OneLineAvatarIconListItem(text="Dark theme")
        self.theme_switch = MDSwitch()
        self.theme_switch.bind(active=lambda *_: self._toggle_theme())
        self.theme_row.add_widget(IconLeftWidget(icon="brightness-4"))
        self.theme_row.add_widget(self.theme_switch)
        content.add_widget(self.theme_row)

        self.palette_row = OneLineAvatarIconListItem(
            text="Primary color",
            on_release=lambda *_: self._open_palette())
        self.palette_row.add_widget(IconLeftWidget(icon="palette"))
        content.add_widget(self.palette_row)

        # ---- library ----
        content.add_widget(MDLabel(
            text="Library", bold=True, adaptive_height=True))
        self.library_info = MDLabel(
            text="", theme_text_color="Secondary",
            font_style="Caption", adaptive_height=True)
        content.add_widget(self.library_info)

        self.clear_row = OneLineAvatarIconListItem(
            text="Clear library",
            on_release=lambda *_: self._confirm_clear())
        self.clear_row.add_widget(IconLeftWidget(icon="delete"))
        content.add_widget(self.clear_row)

        # ---- about ----
        content.add_widget(MDLabel(
            text="About", bold=True, adaptive_height=True))
        sources = ", ".join(s.label for s in REGISTRY.values())
        content.add_widget(MDLabel(
            text=f"NovelFetch\nSources: {sources}",
            theme_text_color="Secondary", font_style="Caption",
            adaptive_height=True))

        body.add_widget(content)
        root = MDBoxLayout(orientation="vertical")
        root.add_widget(self.topbar)
        root.add_widget(body)
        self.add_widget(root)

        # theme_style is set in App.build(), AFTER this tab is constructed;
        # a zero-delay callback runs on the first frame, after on_start.
        Clock.schedule_once(lambda dt: self._refresh(), 0)

    def load(self, **kwargs):
        """goto() tolerance: settings needs no data, but refresh stats."""
        self._refresh()

    def _refresh(self):
        app = MDApp.get_running_app()
        self.theme_switch.active = app.theme_cls.theme_style == "Dark"
        self.palette_row.text = f"Primary color: {app.theme_cls.primary_palette}"
        novels = _scan_library()
        total = sum(n["count"] for n in novels)
        self.library_info.text = f"{len(novels)} novels · {total} files"

    # ---------- appearance ----------

    def _toggle_theme(self):
        app = MDApp.get_running_app()
        if self.theme_switch.active == (app.theme_cls.theme_style == "Dark"):
            return  # programmatic sync from _refresh(), not a user toggle
        app.theme_cls.theme_style = "Dark" if self.theme_switch.active else "Light"
        self._notify("Dark theme" if self.theme_switch.active else "Light theme")

    def _open_palette(self):
        rows = MDList()
        for color in PALETTES:
            rows.add_widget(OneLineAvatarIconListItem(
                text=color,
                on_release=lambda *_, c=color: self._set_palette(c)))
        # Instance ref: a dialog with no strong ref can be GC'd mid-open.
        self._palette_dialog = MDDialog(title="Primary color", type="custom", content_cls=rows)
        self._palette_dialog.open()

    def _set_palette(self, color):
        if self._palette_dialog is not None:
            self._palette_dialog.dismiss()
        MDApp.get_running_app().theme_cls.primary_palette = color
        self._refresh()
        self._notify(f"Primary color: {color}")

    # ---------- library ----------

    def _confirm_clear(self):
        confirm = MDDialog(
            title="Clear library?",
            text="This deletes every downloaded novel and reading progress.",
            buttons=[
                MDFlatButton(text="Cancel", on_release=lambda *_: confirm.dismiss()),
                MDFlatButton(text="Delete",
                             on_release=lambda *_: self._do_clear(confirm)),
            ],
        )
        self._clear_dialog = confirm
        confirm.open()

    def _do_clear(self, dialog):
        dialog.dismiss()
        for novel in _scan_library():
            slug = novel["slug"]
            try:
                shutil.rmtree(os.path.join("novels", slug))
            except OSError:
                pass
            progress.remove(slug)
        for tracked in progress.tracked_novels():
            progress.untrack(tracked["slug"])
        progress.flush()
        self._refresh()
        app = MDApp.get_running_app()
        if hasattr(app.root, "homescreen_library_refresh"):
            app.root.homescreen_library_refresh()
        self._notify("Library cleared")

    # ---------- helpers ----------

    def _notify(self, text):
        MDSnackbar(MDLabel(text=text)).open()
