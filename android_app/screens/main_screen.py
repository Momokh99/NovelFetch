from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen, ScreenManager
from kivymd.app import MDApp
from kivymd.uix.bottomnavigation import (
    MDBottomNavigation,
    MDBottomNavigationItem,
)

from screens.home_tab import HomeTab
from screens.search_tab import SearchTab
from screens.settings_tab import SettingsTab
from screens.update import UpdateTab
from screens.history import HistoryTab
from screens.novel_list import NovelListScreen
from screens.chapter_list import ChapterListScreen
from screens.reader import ReaderScreen
from screens.download_dialog import DownloadProgressScreen


class MainScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.manager = ScreenManager()
        self._stack: list[str] = []   # navigation history; back() pops it

        tabs = Screen(name="tabs")
        self.nav = MDBottomNavigation()
        self.home_tab = HomeTab()
        self.update_tab = UpdateTab()
        self.history_tab = HistoryTab()
        self.nav.add_widget(MDBottomNavigationItem(
            self.home_tab, name="home", text="Home", icon="home"))
        self.search_tab = SearchTab()
        self.nav.add_widget(MDBottomNavigationItem(
            self.search_tab, name="search", text="Search", icon="magnify"))
        self.nav.add_widget(MDBottomNavigationItem(
            self.update_tab, name="updates", text="Updates", icon="update"))
        self.nav.add_widget(MDBottomNavigationItem(
            self.history_tab, name="history", text="History", icon="history"))
        self.nav.add_widget(MDBottomNavigationItem(
            SettingsTab(), name="settings", text="Settings", icon="cog"))
        tabs.add_widget(self.nav)

        self.manager.add_widget(tabs)
        self.manager.add_widget(NovelListScreen(name="novel_list"))
        self.manager.add_widget(ChapterListScreen(name="chapter_list"))
        self.manager.add_widget(ReaderScreen(name="reader"))
        self.manager.add_widget(DownloadProgressScreen(name="download_progress"))

        # Refresh Home whenever the user switches to it in the bottom nav.
        self.nav.bind(on_switch_tabs=self._on_switch_tabs)
        # Android hardware back button (keycode 27) = ESC elsewhere.
        Window.bind(on_keyboard=self._on_key)

        self.add_widget(self.manager)

    def _on_switch_tabs(self, nav, item, name_tab):
        # Kivy prepends the dispatcher instance, so args are (nav, item, name).
        if name_tab == "home":
            self.home_tab.refresh_library()
        elif name_tab == "search":
            self.search_tab.refresh_source()
        elif name_tab == "updates":
            self.update_tab.refresh()
        elif name_tab == "history":
            self.history_tab.refresh()

    def _on_key(self, window, key, scancode, codepoint, modifier):
        if key == 27:  # ESC / Android back
            if self.manager.current != "tabs":
                self.back()
                return True   # consumed: stay in the app
            return False      # on tabs: let the default pause/exit run

    def goto(self, name, **kwargs):
        """Switch to a screen by name, handing it data via load(**kwargs)."""
        if self.manager.current != name:
            self._stack.append(self.manager.current)
        screen = self.manager.get_screen(name)
        if hasattr(screen, "load"):
            screen.load(**kwargs)
        self.manager.current = name

    def back(self):
        """Pop back to the screen we came from (no reload, keeps scroll)."""
        target = self._stack.pop() if self._stack else "tabs"
        if target == "tabs":
            # Returning Home: re-scan so progress/downloads show immediately.
            self.home_tab.refresh_library()
        self.manager.current = target

    def homescreen_library_refresh(self):
        """Called after downloads so the Home tab's library repopulates."""
        self.home_tab.refresh_library()
