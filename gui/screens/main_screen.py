from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivymd.uix.navigationbar import (
    MDNavigationBar,
    MDNavigationItem,
    MDNavigationItemIcon,
    MDNavigationItemLabel,
)

import gui.screens.topbar  # noqa: F401  — registers TopBar in the Factory for KV
from core.progress import progress
from gui.screens.chapter_list import ChapterListScreen
from gui.screens.download_dialog import DownloadProgressScreen
from gui.screens.download_picker import DownloadPickerScreen
from gui.screens.history import HistoryTab
from gui.screens.home_tab import HomeTab
from gui.screens.novel_list import NovelListScreen
from gui.screens.reader import ReaderScreen
from gui.screens.search_tab import SearchTab
from gui.screens.settings_tab import SettingsTab
from gui.screens.update import UpdateTab


class MainScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        self.manager = ScreenManager()
        self._stack: list[str] = []   # navigation history; back() pops it

        tabs = Screen(name="tabs")
        tabs_shell = BoxLayout(orientation="vertical")
        self.tab_manager = ScreenManager()
        self.nav = MDNavigationBar()
        self.home_tab = HomeTab()
        self.update_tab = UpdateTab()
        self.history_tab = HistoryTab()

        self._nav_items = {}  # label text -> screen name

        def _add_tab(content, name, label, icon):
            content.name = name
            self._nav_items[label] = name
            self.tab_manager.add_widget(content)
            item = MDNavigationItem()
            item.add_widget(MDNavigationItemIcon(icon=icon))
            item.add_widget(MDNavigationItemLabel(text=label))
            self.nav.add_widget(item)

        _add_tab(self.home_tab, "home", "Home", "home")
        self.search_tab = SearchTab()
        _add_tab(self.search_tab, "search", "Search", "magnify")
        _add_tab(self.update_tab, "updates", "Updates", "update")
        _add_tab(self.history_tab, "history", "History", "history")
        _add_tab(SettingsTab(), "settings", "Settings", "cog")

        tabs_shell.add_widget(self.tab_manager)
        tabs_shell.add_widget(self.nav)
        tabs.add_widget(tabs_shell)

        self.manager.add_widget(tabs)
        self.manager.add_widget(NovelListScreen(name="novel_list"))
        self.manager.add_widget(ChapterListScreen(name="chapter_list"))
        self.manager.add_widget(ReaderScreen(name="reader"))
        self.manager.add_widget(DownloadProgressScreen(name="download_progress"))
        self.manager.add_widget(DownloadPickerScreen(name="download_picker"))

        # Refresh Home whenever the user switches to it in the bottom nav.
        self.nav.bind(on_switch_tabs=self._on_switch_tabs)
        # Android hardware back button (keycode 27) = ESC elsewhere.
        Window.bind(on_keyboard=self._on_key)

        self.add_widget(self.manager)

    def _on_switch_tabs(self, bar, item, item_icon, item_text):
        if item_text in self._nav_items:
            name = self._nav_items[item_text]
            if name != "home" and self.tab_manager.current == "home":
                # Leaving Home: close its modal states (select mode / batch).
                self.home_tab._leave_home_ui()
            self.tab_manager.current = name
            if name == "home":
                self.home_tab.refresh_library()
            elif name == "search":
                self.search_tab.refresh_source()
            elif name == "history":
                self.history_tab.refresh()

    def _on_key(self, window, key, scancode, codepoint, modifier):
        if key == 27:  # ESC / Android back
            if self.manager.current != "tabs":
                self.back()
                return True   # consumed: stay in the app
            # On tabs: Home's modal states consume the key first.
            if self.tab_manager.current == "home":
                if self.home_tab._batch_active:
                    self.home_tab._cancel_batch()
                    return True
                if self.home_tab._select_mode:
                    self.home_tab._exit_select()
                    return True
            return False      # on tabs: let the default pause/exit run

    def goto(self, name, **kwargs):
        """Switch to a screen by name, handing it data via load(**kwargs)."""
        current = self.manager.current
        if current == "tabs" and self.tab_manager.current == "home":
            # Navigation away from Home closes its modal states so the next
            # visit starts clean (selection does not leak across screens).
            self.home_tab._leave_home_ui()
        if current and current != name:
            self._stack.append(current)
        screen = self.manager.get_screen(name)
        if hasattr(screen, "load"):
            screen.load(**kwargs)
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = name

    def back(self):
        """Pop back to the screen we came from (no reload, keeps scroll)."""
        progress.flush()   # persist read marks on ANY exit (incl. OS/hardware back)
        target = self._stack.pop() if self._stack else "tabs"
        if target == "tabs":
            # Returning Home: re-scan so progress/downloads show immediately.
            self.home_tab.refresh_library()
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = target

    def homescreen_library_refresh(self, force=False):
        """Called after downloads / settings changes so the Home tab's
        library repopulates. pass force=True to rebuild even when nothing on
        disk changed (e.g. layout/grid-size settings)."""
        self.home_tab.refresh_library(force=force)
