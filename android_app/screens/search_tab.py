from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.image import AsyncImage
from kivy.uix.relativelayout import RelativeLayout

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from screens.utils import _snack

from async_runner import async_loop
from screens import utils, theme
from screens.browse import BrowseSection
from screens.source_picker import open_source_picker


class SearchTab(MDScreen):
    """Browse rows + genres on top, with a live search bar above them.
    Search results render inline below the bar; browsing hides while shown.
    Supports pagination: scrolling to the bottom fetches the next page."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._busy = False
        self._debounce = None
        self._clearing = False
        self._query = ""
        self._query_source_name = ""
        self._page = 1
        self._pages = 1
        self._load_more_busy = False
        # Sequence number: bumped on every new search/clear; async responses
        # carrying an older seq are stale and dropped (superseded searches).
        self._seq = 0

        # Widget tree lives in kv/search_tab.kv; alias the runtime-touched nodes.
        self.topbar = self.ids.topbar
        self.source_label = self.ids.source_label
        self.source_btn = self.ids.source_btn
        self.search_field = self.ids.search_field
        self.clear_btn = self.ids.clear_btn
        self.search_progress = self.ids.search_progress
        self.scroll_view = self.ids.scroll_view
        self.browse_box = self.ids.browse_box
        self.results_box = self.ids.results_box
        self.results_list = self.ids.results_list
        self.result_header = self.ids.result_header
        self.result_state_label = self.ids.result_state_label
        self.page_footer = self.ids.page_footer

        self.clear_btn.opacity = 0
        self.clear_btn.disabled = True

        # current_source is set in App.on_start(), AFTER build(). A zero-delay
        # Clock callback fires on the first frame — after on_start has run.
        Clock.schedule_once(lambda dt: self.refresh_source(), 0)

    def _on_scroll_y(self, scroll_y):
        if scroll_y >= 0.05 or not self._query or self._busy or self._load_more_busy:
            return
        # Ignore bottom-hits while the content fits the viewport: layout
        # transitions briefly clamp scroll_y to 0, which would otherwise fire
        # a spurious page-2 fetch right after every result render.
        vp = getattr(self.scroll_view, "_viewport", None)
        if vp is None or vp.height <= self.scroll_view.height:
            return
        self._load_more()

    def _open_source_picker(self):
        open_source_picker()

    # ---------- source switcher ----------

    def refresh_source(self):
        """Update the source-switch button label to the active source."""
        source = MDApp.get_running_app().current_source
        self.source_label.text = f"Source: {source.label}" if source else "No source"
        self.source_btn.icon = "swap-horizontal"

    # ---------- search ----------

    def _on_text_changed(self):
        if self._clearing:
            return
        has_text = bool(self.search_field.text.strip())
        self.clear_btn.opacity = 1 if has_text else 0
        self.clear_btn.disabled = not has_text
        if self._debounce is not None:
            self._debounce.cancel()
        self._debounce = Clock.schedule_once(lambda dt: self._do_search(), 0.7)

    def _on_enter(self):
        if self._debounce is not None:
            self._debounce.cancel()
            self._debounce = None
        self._do_search()

    def _do_search(self):
        query = self.search_field.text.strip()
        if not query:
            return
        source = MDApp.get_running_app().current_source
        if source is None:
            _snack("No source selected.")
            return
        if not source.search_supported:
            _snack("Search is not supported for this source.")
            return

        self._seq += 1
        seq = self._seq
        self._query = query
        self._query_source_name = source.name
        self._page = 1
        self._pages = 1
        self._load_more_busy = False

        async def coro():
            novels, pages = await source.search(query, page=1)
            return novels, pages

        self._busy = True
        self.search_field.disabled = True
        self.search_progress.opacity = 1
        self.result_header.text = ""
        self.page_footer.text = ""
        self.result_state_label.text = f"Searching for '{query}'…"
        if self.browse_box.parent is not None:
            self.browse_box.parent.remove_widget(self.browse_box)
        self.results_box.opacity = 1
        self.results_box.disabled = False
        self.results_list.clear_widgets()
        async_loop.run(
            coro(), lambda res, err, s=seq: self._on_first_page(res, err, s),
            timeout=30)

    def _on_first_page(self, result, error, seq):
        if seq != self._seq:
            return
        self._busy = False
        self.search_field.disabled = False
        self.search_progress.opacity = 0
        source = MDApp.get_running_app().current_source
        blocked = getattr(source, "blocked", False)
        if error is not None:
            self._clear_results()
            _snack("Search failed. Check your connection.")
        elif blocked:
            self._clear_results()
            _snack(f"{source.label} is blocked by anti-bot protection.")
        elif not result:
            self.result_header.text = ""
            self.result_state_label.text = f"No results for '{self._query}'"
            self.page_footer.text = ""
            self.results_list.clear_widgets()
            self.results_box.opacity = 1
            self.results_box.disabled = False
        else:
            novels, pages = result
            self._pages = pages or 1
            self.result_header.text = f"{len(novels)} result(s) for '{self._query}'"
            self.result_state_label.text = ""
            self._update_footer()
            self._show_results(novels)

    def _load_more(self):
        if self._load_more_busy or self._busy:
            return
        if self._page >= self._pages:
            return
        source = MDApp.get_running_app().current_source
        # Pin pagination to the source the query ran on: switching sources
        # mid-results must never fetch page 2 of the old query from a new one.
        if source is None or not source.search_supported \
                or source.name != self._query_source_name:
            return
        next_page = self._page + 1
        self._seq += 1
        seq = self._seq

        async def coro():
            novels, pages = await source.search(self._query, page=next_page)
            return novels, pages

        self._load_more_busy = True
        self.search_progress.opacity = 1
        self.page_footer.text = f"Page {self._page} of {self._pages} · Loading more…"
        async_loop.run(coro(), lambda res, err, s=seq: self._on_more_done(res, err, s),
                       timeout=30)

    def _on_more_done(self, result, error, seq):
        if seq != self._seq:
            return
        self._load_more_busy = False
        self.search_progress.opacity = 0
        if error is not None or not result:
            self._update_footer()
            return
        novels, pages = result
        self._page += 1
        self._pages = pages or self._pages
        for n in novels:
            self.results_list.add_widget(self._make_row(n))
        self._update_footer()

    def _update_footer(self):
        if self._page >= self._pages:
            self.page_footer.text = ""
        else:
            self.page_footer.text = f"Page {self._page} of {self._pages}"

    # ---------- inline results ----------

    def _show_results(self, novels):
        self.results_list.clear_widgets()
        self.result_state_label.text = ""
        for n in novels:
            self.results_list.add_widget(self._make_row(n))
        # Swap: drop browse, surface results right under the search bar.
        if self.browse_box.parent is not None:
            self.browse_box.parent.remove_widget(self.browse_box)
        self.results_box.opacity = 1
        self.results_box.disabled = False

    def _make_row(self, novel):
        row = MDCard(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(120),
            padding=theme.CARD_PAD, spacing=theme.CARD_GAP,
        )
        cover = novel.get("cover", "") or ""
        img = AsyncImage(
            source="",
            size_hint=(None, 1),
            width=dp(70),
            keep_ratio=True,
            allow_stretch=True,
        )
        if cover:
            utils.set_image_url(img, cover)

        source = MDApp.get_running_app().current_source
        qualified = source.qualify_slug(novel["slug"]) if source else ""
        registered = bool(qualified and utils._read_meta(qualified))

        if registered:
            row.md_bg_color = theme.library_highlight()

        texts = MDBoxLayout(orientation="vertical", size_hint_y=None, adaptive_height=True, spacing="2dp",
                            pos_hint={"center_x": 0.5, "center_y": 0.5})
        texts.add_widget(MDLabel(
            text=novel["title"], bold=True,
            font_style="Title", role="small", size_hint_y=None, height="28dp",
            shorten=True, shorten_from="right", max_lines=1))
        sub = novel.get("author", "") or ""
        if novel.get("latest"):
            sub += f"  ·  {novel['latest']}"
        texts.add_widget(MDLabel(
            text=sub, theme_text_color="Secondary",
            font_style="Label", role="large", size_hint_y=None, height="22dp"))
        texts_rl = RelativeLayout(size_hint=(1, 1))
        texts_rl.add_widget(texts)
        row.add_widget(img)
        row.add_widget(texts_rl)
        row.add_widget(utils._add_to_library_icon(novel, source))
        row.on_release = lambda n=novel: self._open(n)
        return row

    def _open(self, novel):
        # Tapping a result drills into the chapter list (full screen, as before).
        source = MDApp.get_running_app().current_source
        utils._open_chapters_for(
            novel, source,
            set_loading=lambda s: setattr(self.results_list, "disabled", s))

    def _clear_results(self):
        self.results_list.clear_widgets()
        self.result_header.text = ""
        self.result_state_label.text = ""
        self.page_footer.text = ""
        self.results_box.opacity = 0
        self.results_box.disabled = True
        if self.results_box.parent is not None and self.browse_box.parent is None:
            self.results_box.parent.add_widget(self.browse_box)

    def _clear(self):
        if self._debounce is not None:
            self._debounce.cancel()
            self._debounce = None
        self._clearing = True
        self.search_field.text = ""
        self._clearing = False
        self.clear_btn.opacity = 0
        self.clear_btn.disabled = True
        self._seq += 1
        self._busy = False
        self._load_more_busy = False
        self.search_field.disabled = False
        self.search_progress.opacity = 0
        self._query = ""
        self._query_source_name = ""
        self._page = 1
        self._pages = 1
        self.result_header.text = ""
        self.result_state_label.text = ""
        self.page_footer.text = ""
        self._clear_results()
