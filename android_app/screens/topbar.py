from kivy.factory import Factory
from kivy.properties import BooleanProperty, StringProperty
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton


class TopBar(MDBoxLayout):
    """Slim top bar shared by every screen: optional back arrow, an
    ellipsized title, and a row of right-aligned action icon buttons.

    Unlike MDTopAppBar, this is a plain MDBoxLayout that sits at the top of
    a vertical root layout instead of relying on hidden pos_hint behavior.

    The widget tree lives in kv/topbar.kv; this class only exposes the
    ``title``/``back`` properties and the action-button plumbing the Python
    side needs. The back arrow is a Python-only child (KivyMD's
    ``<MDIconButton>`` rule forces ``size: 48, 48``, so a KV-side conditional
    cannot collapse it cleanly) and is added once via a ``back``-property bind
    so it works whether the TopBar is built by Python or declared in KV."""

    title = StringProperty("")
    back = BooleanProperty(False)

    def __init__(self, title="", back=False, on_back=None, actions=None, **kwargs):
        super().__init__(**kwargs)
        self._back_btn = None
        self.bind(back=self._sync_back)
        self.title = title
        self.back = back
        self._on_back = on_back
        self._action_buttons = []
        if actions:
            self.set_actions(actions)

    def on_kv_post(self, base_widget):
        # KV declares `back: True` on the rule, applied before this runs; make
        # sure the button reflects it (Python path re-triggers via the bind).
        if self.back:
            self._sync_back()

    def _sync_back(self, *args):
        if self._back_btn is not None:
            self.remove_widget(self._back_btn)
            self._back_btn = None
        if self.back:
            self._back_btn = MDIconButton(
                icon="arrow-left", on_release=lambda *_: self._go_back())
            # Children list is reverse-ordered; appending puts the arrow
            # leftmost in the horizontal layout, matching the Python-only bar.
            self.add_widget(self._back_btn, index=len(self.children))

    def _go_back(self):
        if self._on_back is not None:
            self._on_back()
        else:
            MDApp.get_running_app().back()

    def set_title(self, text):
        self.ids.title_label.text = text

    def set_actions(self, actions):
        self.ids.actions_box.clear_widgets()
        self._action_buttons = []
        for icon, cb in actions:
            btn = MDIconButton(icon=icon, on_release=lambda *_, c=cb: c())
            self._action_buttons.append(btn)
            self.ids.actions_box.add_widget(btn)


Factory.register("TopBar", cls=TopBar, module="screens.topbar")