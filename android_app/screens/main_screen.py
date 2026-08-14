from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen, ScreenManager
from kivymd.app import MDApp
from kivymd.uix.bottomnavigation import (
    MDBottomNavigation,
    MDBottomNavigationItem,
)
from kivymd.uix.label import MDLabel

from screens.home_tab import HomeTab
from screens.search_tab import SearchTab
from screens.novel_list import NovelListScreen
from screens.chapter_list import ChapterListScreen


def _placeholder(title: str) -> MDLabel:
    return MDLabel(text=f"{title} — coming soon", halign="center")


class MainScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.manager = ScreenManager()
        self._previous = "tabs"   # screen to return to via back()

        tabs = Screen(name="tabs")
        self.nav = MDBottomNavigation()
        self.home_tab = HomeTab()
        self.nav.add_widget(MDBottomNavigationItem(
            self.home_tab, name="home", text="Home", icon="home"))
        self.nav.add_widget(MDBottomNavigationItem(
            SearchTab(), name="search", text="Search", icon="magnify"))
        self.nav.add_widget(MDBottomNavigationItem(
            _placeholder("Settings"), name="settings", text="Settings", icon="cog"))
        tabs.add_widget(self.nav)

        self.manager.add_widget(tabs)
        self.manager.add_widget(NovelListScreen(name="novel_list"))
        self.manager.add_widget(ChapterListScreen(name="chapter_list"))

        self.add_widget(self.manager)

    def goto(self, name, **kwargs):
        """Switch to a screen by name, handing it data via load(**kwargs)."""
        if self.manager.current != name:
            self._previous = self.manager.current
            if name == "tabs":
                # Returning Home: re-scan so downloads/deletes show immediately.
                self.home_tab.refresh_library()
        screen = self.manager.get_screen(name)
        if hasattr(screen, "load"):
            screen.load(**kwargs)
        self.manager.current = name

    def back(self):
        """Pop back to the screen we came from (no reload, keeps scroll)."""
        self.manager.current = self._previous or "tabs"

    def homescreen_library_refresh(self):
        """Called after downloads so the Home tab's library repopulates."""
        self.home_tab.refresh_library()
