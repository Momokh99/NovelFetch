"""Tests for the Settings "Show continue reading" switch (right-aligned,
persistent, and synced on refresh)."""

import json
import os
import sys

import pytest
from kivy.core.window import Window
from kivy.lang import Builder
from kivymd.app import MDApp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "android_app")


class _SettingsApp(MDApp):
    def build(self):
        Builder.load_file(os.path.join(APP, "kv/settings_tab.kv"))
        Builder.load_file(os.path.join(APP, "kv/topbar.kv"))
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Teal"
        from screens.settings_tab import SettingsTab
        return SettingsTab()


@pytest.fixture
def tab(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("novels", exist_ok=True)
    app = _SettingsApp()
    import kivy
    kivy.app.App._app_instance = app
    win = app.build()
    Window.add_widget(win)
    win.pos = (0, 0)
    win.size = Window.size
    win._refresh()
    yield win


def saved():
    return json.loads(open("app_settings.json").read()).get("show_continue_reading")


def test_switch_sits_on_right_side_of_row(tab):
    switch = tab.ids.continue_reading_switch
    assert switch.pos_hint.get("center_y") == 0.5
    assert switch.pos_hint.get("right") == 1
    assert switch.size != (0, 0)


def test_switch_starts_matching_saved_state(tab):
    assert tab.ids.continue_reading_switch.active is True  # default is True


def test_switch_off_toggles_and_persists(tab):
    switch = tab.ids.continue_reading_switch
    switch.active = False  # what the thumb tap does
    tab._toggle_continue_reading()
    assert saved() is False
    tab._refresh()
    assert switch.active is False


def test_switch_on_toggles_and_persists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("novels", exist_ok=True)
    json.dump({"show_continue_reading": False}, open("app_settings.json", "w"))
    app = _SettingsApp()
    import kivy
    kivy.app.App._app_instance = app
    win = app.build()
    Window.add_widget(win)
    win.pos = (0, 0)
    win.size = Window.size
    win._refresh()
    switch = win.ids.continue_reading_switch
    assert switch.active is False
    switch.active = True
    win._toggle_continue_reading()
    assert saved() is True