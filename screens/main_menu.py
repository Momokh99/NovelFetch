from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Static, RadioSet, RadioButton, LoadingIndicator, Footer
from textual.containers import Vertical
from sources import REGISTRY
from screens.shared import CustomHeader

class MainMenu(Screen):
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("tab", "next_option", "", show=False),
        Binding("shift+tab", "prev_option", "", show=False),
        Binding("s", "switch_source", "Switch Source"),
    ]

    def compose(self):
        yield CustomHeader()
        with Vertical():
            yield Static(list(REGISTRY.values())[0].ascii_art, classes="banner")
            yield Static("Action:", classes="title")
            yield RadioSet(
                RadioButton("Search by name"),
                RadioButton("Hot novels"),
                RadioButton("Latest releases"),
                RadioButton("Most popular"),
                RadioButton("Completed novels"),
                RadioButton("Browse by genre"),
                RadioButton("My Library"),
                id="action-selector"
            )
            yield LoadingIndicator(classes="loading")
        yield Footer()

    async def on_radio_set_changed(self, event: RadioSet.Changed):
        idx = event.index
        if idx in (1, 2, 3, 4):
            self.query_one("#action-selector", RadioSet).disabled = True
            self.query_one(LoadingIndicator).set_class(True, "-visible")
            try:
                source = self.app.current_source
                key = ["hot", "latest", "popular", "completed"][idx - 1]
                soup = await source.fetch_url(source.browse_urls[key])
                novels = source.extract_novel_rows(soup)
                from screens.browse import NovelListScreen
                self.app.push_screen(NovelListScreen(novels, source=source))
            except Exception:
                self.notify("Failed to fetch novels. Check your connection.", timeout=3)
            finally:
                self.query_one(LoadingIndicator).set_class(False, "-visible")
                self.query_one("#action-selector", RadioSet).disabled = False
        elif idx == 5:
            from screens.browse import GenreScreen
            self.app.push_screen(GenreScreen(source=self.app.current_source))
        elif idx == 0:
            from screens.browse import SearchScreen
            self.app.push_screen(SearchScreen(source=self.app.current_source))
        elif idx == 6:
            from screens.library import MyLibraryScreen
            self.app.push_screen(MyLibraryScreen())

    def action_quit(self):
        self.app.exit()

    def action_next_option(self):
        self.query_one("#action-selector", RadioSet).action_next_button()

    def action_prev_option(self):
        self.query_one("#action-selector", RadioSet).action_previous_button()
    def on_mount(self):
        self.app.current_source = list(REGISTRY.values())[0]
        self.query_one("#action-selector", RadioSet).focus()
    def action_switch_source(self):
        sources = list(REGISTRY.values())
        current = self.app.current_source
        idx = sources.index(current)
        next_idx = (idx + 1) % len(sources)
        self.app.current_source = sources[next_idx]
        self.query_one(".banner", Static).update(sources[next_idx].ascii_art)
        self.notify(f"Switched to {sources[next_idx].label}")
