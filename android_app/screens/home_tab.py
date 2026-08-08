from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel

class HomeTab(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(MDLabel(text="Home — coming soon", halign="center"))
