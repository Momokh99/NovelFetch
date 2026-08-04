from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager
from kivy.uix.boxlayout import BoxLayout
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.uix.screen import MDScreen

class PlaceholderScreen(MDScreen):
    def __init__(self, title, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(Label(text=f"{title} — coming soon", font_size="20sp"))


class MainScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

    nav = MDBottomNavigation()
        nav.add_widget(MDBottomNavigationItem(PlaceholderScreen("Home"),   text="Home",   icon="home"))
        nav.add_widget(MDBottomNavigationItem(PlaceholderScreen("Search"), text="Search", icon="magnify"))
        nav.add_widget(MDBottomNavigationItem(PlaceholderScreen("Settings"), text="Settings", icon="cog"))
        self.add_widget(nav)


