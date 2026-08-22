import os
import shutil

from kivy.clock import Clock
from kivy.properties import StringProperty

from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, OneLineAvatarIconListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar

from progress import progress, _scan_library
from async_runner import async_loop
from sources import REGISTRY

PALETTES = [
    "Red", "Pink", "Purple", "DeepPurple", "Indigo", "Blue", "LightBlue",
    "Cyan", "Teal", "Green", "LightGreen", "Lime", "Yellow", "Amber",
    "Orange", "DeepOrange", "Brown", "Grey", "BlueGrey",
]


class SettingsTab(MDScreen):
    """Appearance (theme/palette) and library management."""

    about_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._palette_dialog = None
        self._clear_dialog = None

        # Widget tree lives in kv/settings_tab.kv; alias the runtime-touched
        # nodes so the rest of this file keeps working unchanged.
        self.topbar = self.ids.topbar
        self.theme_switch = self.ids.theme_switch
        self.palette_row = self.ids.palette_row
        self.library_info = self.ids.library_info
        self.about_text = "NovelFetch\nSources: " + ", ".join(
            s.label for s in REGISTRY.values())

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

        async def coro():
            novels = _scan_library()
            total = sum(n["count"] for n in novels)
            return len(novels), total

        def on_done(result, error):
            if error is not None:
                return
            count, total = result
            self.library_info.text = f"{count} novels · {total} files"

        async_loop.run(coro(), on_done, timeout=10)

    # ---------- appearance ----------

    def _toggle_theme(self):
        app = MDApp.get_running_app()
        if self.theme_switch.active == (app.theme_cls.theme_style == "Dark"):
            return  # programmatic sync from _refresh(), not a user toggle
        app.theme_cls.theme_style = "Dark" if self.theme_switch.active else "Light"
        from screens.app_settings import save_settings
        save_settings(theme_style=app.theme_cls.theme_style)
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
        from screens.app_settings import save_settings
        save_settings(primary_palette=color)
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
