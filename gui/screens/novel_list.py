from kivymd.uix.screen import MDScreen

from gui.screens import utils


class NovelListScreen(MDScreen):
    """Search/browse results. Data arrives via load(), the goto() contract."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.novels = []
        self.source = None

        self.topbar = self.ids.topbar
        self.list_view = self.ids.list_view
        self.empty_box = self.ids.empty_box

    def load(self, novels, source=None, title="Results"):
        # Populated fresh on every goto("novel_list", ...) call.
        self.novels = novels
        self.source = source
        self.topbar.set_title(f"{title} ({len(novels)})" if novels else title)
        self.list_view.clear_widgets()
        if not novels:
            self.empty_box.opacity = 1
            self.empty_box.height = self.empty_box.minimum_height
        else:
            self.empty_box.opacity = 0
            self.empty_box.height = 0
        for n in novels:
            self.list_view.add_widget(self._make_row(n))

    def _make_row(self, novel):
        row = utils.make_novel_card(novel, self.source)
        row.on_release = lambda n=novel: self._open(n)
        return row

    def _open(self, novel):
        # Basic guard: disable further taps while one fetch is in flight.
        source = self.source or utils._get_source(novel.get("slug", ""))
        utils._open_chapters_for(
            novel, source, set_loading=lambda s: setattr(self.list_view, "disabled", s)
        )
