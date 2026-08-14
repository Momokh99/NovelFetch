from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, TwoLineAvatarListItem, IconLeftWidget
from kivymd.uix.snackbar import MDSnackbar

from sources import REGISTRY


# Module-level ref: a dialog with no strong ref can be GC'd mid-open.
_dialog = None


def open_source_picker():
    """Modal list of every source from the shared REGISTRY.

    A function, not a class: the dialog is transient UI. HomeTab only needs
    'open it' — everything else lives here, keeping HomeTab small.
    """
    app = MDApp.get_running_app()
    def on_select(source):
        app.current_source = source
        _dialog.dismiss()
        MDSnackbar(MDLabel(text=f"Switched to {source.label}")).open()

    content = MDList()
    for source in REGISTRY.values():
        current = source is app.current_source   # identity compare is enough
        item = TwoLineAvatarListItem(
            text=("✓ " if current else "") + source.label,
            secondary_text=f"{len(source.browse_urls)} browse lists · "
                           f"{len(source.genres)} genres",
            on_release=lambda *_, s=source: on_select(s),   # bind NOW, not later
        )
        item.add_widget(IconLeftWidget(icon="book-open-variant"))
        content.add_widget(item)

    global _dialog
    _dialog = MDDialog(title="Select source", type="custom", content_cls=content)
    _dialog.open()
