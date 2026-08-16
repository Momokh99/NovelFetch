from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDLabel


class TopBar(MDBoxLayout):
    """Slim top bar shared by every screen: optional back arrow, an
    ellipsized title, and a row of right-aligned action icon buttons.

    Unlike MDTopAppBar, this is a plain MDBoxLayout that sits at the top of
    a vertical root layout instead of relying on hidden pos_hint behavior."""

    def __init__(self, title="", back=False, on_back=None, actions=None, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None, height="48dp",
            padding=("4dp", "0dp", "4dp", "0dp"),
            spacing="4dp",
            **kwargs,
        )
        self._on_back = on_back

        if back:
            self.back_btn = MDIconButton(
                icon="arrow-left", on_release=lambda *_: self._go_back())
            self.add_widget(self.back_btn)

        self.title_label = MDLabel(
            text=title,
            font_style="Subtitle2",
            theme_text_color="Secondary",
            halign="left", valign="middle",
            size_hint_x=1,
            shorten=True, shorten_from="center", max_lines=1,
        )
        self.title_label.bind(
            width=lambda *_: setattr(
                self.title_label, "text_size", (self.title_label.width, None)))
        self.add_widget(self.title_label)

        self._actions_box = MDBoxLayout(
            orientation="horizontal", adaptive_width=True, spacing="2dp")
        self.add_widget(self._actions_box)
        self._action_buttons = []
        if actions:
            self.set_actions(actions)

    def _go_back(self):
        if self._on_back is not None:
            self._on_back()

    def set_title(self, text):
        self.title_label.text = text

    def set_actions(self, actions):
        self._actions_box.clear_widgets()
        self._action_buttons = []
        for icon, cb in actions:
            btn = MDIconButton(icon=icon, on_release=lambda *_, c=cb: c())
            self._action_buttons.append(btn)
            self._actions_box.add_widget(btn)