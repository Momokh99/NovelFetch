from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogContentContainer,
    MDDialogHeadlineText,
)
from kivymd.uix.label import MDLabel
from kivymd.uix.list import (
    MDList,
    MDListItem,
    MDListItemHeadlineText,
    MDListItemLeadingIcon,
    MDListItemSupportingText,
)

from gui.screens.utils import _snack
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
        _snack(f"Switched to {source.label}")
        root = app.root
        if hasattr(root, "search_tab"):
            root.search_tab.refresh_source()

    content = MDList()
    for source in REGISTRY.values():
        current = source is app.current_source   # identity compare is enough
        item = MDListItem(
            MDListItemLeadingIcon(icon="book-open-variant"),
            MDListItemHeadlineText(text=("✓ " if current else "") + source.label),
            MDListItemSupportingText(
                text=f"{len(source.browse_urls)} browse lists · "
                     f"{len(source.genres)} genres"),
            on_release=lambda *_, s=source: on_select(s),
        )
        content.add_widget(item)

    global _dialog
    _dialog = MDDialog(
        MDDialogHeadlineText(
            text="Select source",
            halign="left",
        ),
        MDDialogContentContainer(content),
    )
    _dialog.open()
