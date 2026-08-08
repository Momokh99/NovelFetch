from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen, ScreenManager
from kivymd.app import MDApp
from kivymd.uix.bottomnavigation import (
    MDBottomNavigation,
    MDBottomNavigationItem,
)
from kivymd.uix.label import MDLabel

from screens.home_tab import HomeTab
from screens.novel_list import NovelListScreen
from screens.chapter_list import ChapterListScreen


def _placeholder(title: str) -> MDLabel:
    return MDLabel(text=f"{title} — coming soon", halign="center")


class MainScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.manager = ScreenManager()

        tabs = Screen(name="tabs")
        self.nav = MDBottomNavigation()
        self.nav.add_widget(MDBottomNavigationItem(
            HomeTab(), name="home", text="Home", icon="home"))
        self.nav.add_widget(MDBottomNavigationItem(
            _placeholder("Search"), name="search", text="Search", icon="magnify"))
        self.nav.add_widget(MDBottomNavigationItem(
            _placeholder("Settings"), name="settings", text="Settings", icon="cog"))
        tabs.add_widget(self.nav)

        self.manager.add_widget(tabs)
        self.manager.add_widget(NovelListScreen(name="novel_list"))
        self.manager.add_widget(ChapterListScreen(name="chapter_list"))

        self.add_widget(self.manager)

    def goto(self, name, **kwargs):
        """Switch to a screen by name, handing it data via load(**kwargs)."""
        screen = self.manager.get_screen(name)
        if hasattr(screen, "load"):
            screen.load(**kwargs)
        self.manager.current = name

