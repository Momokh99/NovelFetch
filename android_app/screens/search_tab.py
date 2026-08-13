from kivymd.uix.screen import MDScreen
from kivymd.uix.toolbar import MDTopAppBar

from screens.browse import BrowseSection


class SearchTab(MDScreen):
    """Mirrors Home's discovery block (browse rows + genres), no library."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.topbar = MDTopAppBar(title="Search")
        self.add_widget(self.topbar)
        self.add_widget(BrowseSection())
