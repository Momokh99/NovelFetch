import os
import shutil

from kivy.clock import Clock
from kivy.properties import StringProperty

from kivymd.app import MDApp
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogHeadlineText,
    MDDialogSupportingText,
    MDDialogButtonContainer,
    MDDialogContentContainer,
)
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, MDListItem, MDListItemHeadlineText
from kivymd.uix.screen import MDScreen
from screens.utils import _snack

from progress import progress, _scan_library
from async_runner import async_loop
from sources import REGISTRY
from screens.app_settings import load_settings, save_settings

PALETTES = [
    "Red", "Pink", "Purple", "DeepPurple", "Indigo", "Blue", "LightBlue",
    "Cyan", "Teal", "Green", "LightGreen", "Lime", "Yellow", "Amber",
    "Orange", "DeepOrange", "Brown", "Grey", "BlueGrey",
]

HOME_LAYOUTS = [
    ("A", "Cards"),
    ("B", "List"),
]

READ_INDICATORS = [
    ("off", "Off"),
    ("text", "Text"),
    ("linear", "Linear bar"),
    ("percentage", "Percentage"),
    ("blocks", "Segmented blocks"),
    ("dots", "Segmented dots"),
    ("wave", "Wave fill"),
]

CARD_GRID_SIZES = [
    ("large", "Large (1 per row)"),
    ("medium", "Medium (2 per row)"),
    ("small", "Small (3 per row)"),
]


def _home_layout_label(layout):
    for key, label in HOME_LAYOUTS:
        if key == layout:
            return label
    return layout


def _read_indicator_label(key):
    for k, label in READ_INDICATORS:
        if k == key:
            return label
    return key


def _grid_size_label(key):
    for k, label in CARD_GRID_SIZES:
        if k == key:
            return label
    return key


class SettingsTab(MDScreen):
    """Appearance (theme/palette) and library management."""

    about_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._palette_dialog = None
        self._clear_dialog = None
        self._layout_dialog = None
        self._read_indicator_dialog = None
        self._grid_size_dialog = None

        # Widget tree lives in kv/settings_tab.kv; alias the runtime-touched
        # nodes so the rest of this file keeps working unchanged.
        self.topbar = self.ids.topbar
        self.theme_switch = self.ids.theme_switch
        self.palette_row = self.ids.palette_row
        self.read_indicator_row = self.ids.read_indicator_row
        self.grid_size_row = self.ids.grid_size_row
        self.home_layout_row = self.ids.home_layout_row
        self.continue_reading_switch = self.ids.continue_reading_switch
        self.update_and_download_switch = self.ids.update_and_download_switch
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
        if app is None:
            return
        self.theme_switch.active = app.theme_cls.theme_style == "Dark"
        self.palette_row.text = f"Primary color: {app.theme_cls.primary_palette}"
        settings = load_settings()
        self.read_indicator_row.text = \
            f"Read indicator: {_read_indicator_label(settings.get('read_indicator', 'off'))}"
        self.grid_size_row.text = \
            f"Card grid size: {_grid_size_label(settings.get('card_grid_size', 'medium'))}"
        self.home_layout_row.text = \
            f"Home layout: {_home_layout_label(settings.get('home_layout', 'A'))}"
        self.continue_reading_switch.active = \
            bool(settings.get("show_continue_reading", True))
        self.update_and_download_switch.active = \
            bool(settings.get("update_and_download", False))

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
        save_settings(theme_style=app.theme_cls.theme_style)
        self._notify("Dark theme" if self.theme_switch.active else "Light theme")

    def _open_palette(self):
        rows = MDList()
        for color in PALETTES:
            rows.add_widget(MDListItem(MDListItemHeadlineText(
                text=color,
            ), on_release=lambda *_, c=color: self._set_palette(c)))
        # Instance ref: a dialog with no strong ref can be GC'd mid-open.
        self._palette_dialog = MDDialog(
            MDDialogHeadlineText(
                text="Primary color",
                halign="left",
            ),
            MDDialogContentContainer(rows),
        )
        self._palette_dialog.open()

    def _set_palette(self, color):
        if self._palette_dialog is not None:
            self._palette_dialog.dismiss()
        MDApp.get_running_app().theme_cls.primary_palette = color
        save_settings(primary_palette=color)
        self._refresh()
        self._notify(f"Primary color: {color}")

    def _open_home_layout(self):
        rows = MDList()
        current = load_settings().get("home_layout", "A")
        for key, label in HOME_LAYOUTS:
            rows.add_widget(MDListItem(MDListItemHeadlineText(
                text=label + (" ✓" if key == current else ""),
            ), on_release=lambda *_, k=key: self._set_home_layout(k)))
        self._layout_dialog = MDDialog(
            MDDialogHeadlineText(
                text="Home layout",
                halign="left",
            ),
            MDDialogContentContainer(rows),
        )
        self._layout_dialog.open()

    def _set_home_layout(self, key):
        if self._layout_dialog is not None:
            self._layout_dialog.dismiss()
        save_settings(home_layout=key)
        self._refresh()
        app = MDApp.get_running_app()
        if hasattr(app.root, "homescreen_library_refresh"):
            # Disk didn't change — force the Home tab to apply the new layout.
            app.root.homescreen_library_refresh(force=True)
        self._notify(f"Home layout: {_home_layout_label(key)}")

    def _open_read_indicator(self):
        rows = MDList()
        current = load_settings().get("read_indicator", "off")
        for key, label in READ_INDICATORS:
            rows.add_widget(MDListItem(MDListItemHeadlineText(
                text=label + (" ✓" if key == current else ""),
            ), on_release=lambda *_, k=key: self._set_read_indicator(k)))
        self._read_indicator_dialog = MDDialog(
            MDDialogHeadlineText(
                text="Read indicator",
                halign="left",
            ),
            MDDialogContentContainer(rows),
        )
        self._read_indicator_dialog.open()

    def _set_read_indicator(self, key):
        if self._read_indicator_dialog is not None:
            self._read_indicator_dialog.dismiss()
        save_settings(read_indicator=key)
        self._refresh()
        app = MDApp.get_running_app()
        if hasattr(app.root, "homescreen_library_refresh"):
            app.root.homescreen_library_refresh()
        self._notify(f"Read indicator: {_read_indicator_label(key)}")

    def _open_grid_size(self):
        rows = MDList()
        current = load_settings().get("card_grid_size", "medium")
        for key, label in CARD_GRID_SIZES:
            rows.add_widget(MDListItem(MDListItemHeadlineText(
                text=label + (" ✓" if key == current else ""),
            ), on_release=lambda *_, k=key: self._set_grid_size(k)))
        self._grid_size_dialog = MDDialog(
            MDDialogHeadlineText(
                text="Card grid size",
                halign="left",
            ),
            MDDialogContentContainer(rows),
        )
        self._grid_size_dialog.open()

    def _set_grid_size(self, key):
        if self._grid_size_dialog is not None:
            self._grid_size_dialog.dismiss()
        save_settings(card_grid_size=key)
        self._refresh()
        app = MDApp.get_running_app()
        if hasattr(app.root, "homescreen_library_refresh"):
            app.root.homescreen_library_refresh(force=True)
        self._notify(f"Card grid: {_grid_size_label(key)}")

    def _toggle_continue_reading(self):
        app = MDApp.get_running_app()
        if self.continue_reading_switch.active == load_settings().get("show_continue_reading", True):
            return  # programmatic sync from _refresh(), not a user toggle
        save_settings(show_continue_reading=self.continue_reading_switch.active)
        self._refresh()
        if hasattr(app.root, "homescreen_library_refresh"):
            app.root.homescreen_library_refresh(force=True)
        self._notify("Continue reading: on" if self.continue_reading_switch.active else "Continue reading: off")

    def _toggle_update_and_download(self):
        app = MDApp.get_running_app()
        if self.update_and_download_switch.active == load_settings().get("update_and_download", False):
            return  # programmatic sync from _refresh(), not a user toggle
        save_settings(update_and_download=self.update_and_download_switch.active)
        self._refresh()
        self._notify("Update & download: on" if self.update_and_download_switch.active else "Update & download: off")

    # ---------- library ----------

    def _confirm_clear(self):
        confirm = MDDialog(
            MDDialogHeadlineText(
                text="Clear library?",
                halign="left",
            ),
            MDDialogSupportingText(
                text="This deletes every downloaded novel and reading progress.",
                halign="left",
            ),
            MDDialogButtonContainer(
                MDButton(MDButtonText(text="Cancel"), style="text",
                         on_release=lambda *_: confirm.dismiss()),
                MDButton(MDButtonText(text="Delete"), style="text",
                         on_release=lambda *_: self._do_clear(confirm)),
                spacing="8dp",
            ),
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
        _snack(text)
