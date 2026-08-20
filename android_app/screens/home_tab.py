import os

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.fitimage import FitImage
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.list import MDList
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.screen import MDScreen

from progress import _scan_library, progress
from screens import utils                    # _get_source helper, meta
from screens import theme
from screens.novel_list import _TapCard
from screens.source_picker import open_source_picker
from screens.topbar import TopBar


class HomeTab(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.topbar = TopBar(
            title="NovelFetch",
            actions=[("book-open-variant", open_source_picker)],
        )

        body = ScrollView(always_overscroll=False)
        content = MDBoxLayout(orientation="vertical", adaptive_height=True,
                              padding=theme.TAB_CONTENT_PAD, spacing=theme.SECTION_GAP)

        content.add_widget(MDLabel(text="My Library", bold=True, adaptive_height=True))
        self.library_count = MDLabel(
            text="", theme_text_color="Secondary",
            font_style="Caption", adaptive_height=True)
        content.add_widget(self.library_count)

        self.library_empty = MDBoxLayout(
            orientation="vertical", adaptive_height=True,
            padding="16dp", spacing="4dp")
        self.library_empty.add_widget(MDIcon(
            icon="bookshelf", halign="center", font_size="56dp",
            theme_text_color="Secondary"))
        self.library_empty.add_widget(MDLabel(
            text="Your library is empty", halign="center",
            bold=True, adaptive_height=True))
        self.library_empty.add_widget(MDLabel(
            text="Browse the hot list or search for novels\nto start reading.",
            halign="center", theme_text_color="Secondary",
            font_style="Caption", adaptive_height=True))
        content.add_widget(self.library_empty)

        self.library_list = MDList()
        content.add_widget(self.library_list)

        body.add_widget(content)
        root = MDBoxLayout(orientation="vertical")
        root.add_widget(self.topbar)
        root.add_widget(body)
        self.add_widget(root)

        # current_source is set in App.on_start(), AFTER build(). A zero-delay
        # Clock callback fires on the first frame — after on_start has run.
        Clock.schedule_once(lambda dt: self.refresh_library(), 0)

    # ---------- library ----------

    def refresh_library(self):
        # _library_entries() walks novels/ synchronously — cheap, thread-safe —
        # and includes tracked slugs whose files were deleted.
        novels = utils._library_entries()
        self.library_list.clear_widgets()

        n_tracked = sum(
            1 for n in novels
            if utils._is_tracked(n["slug"])
            and not utils._has_chapters(n["slug"])
        )
        if novels:
            self.library_empty.size_hint_y = None
            self.library_empty.height = 0
            self.library_empty.opacity = 0
            self.library_empty.disabled = True
            count_text = f"{len(novels)} novel{'s' if len(novels) != 1 else ''}"
            if n_tracked:
                count_text += f" · {n_tracked} tracked"
            self.library_count.text = count_text
        else:
            self.library_empty.adaptive_height = True
            self.library_empty.opacity = 1
            self.library_empty.disabled = False
            self.library_count.text = ""

        for n in novels:
            slug = n["slug"]
            meta = utils._read_meta(slug)   # {"title", "cover", "chapters"} or {}
            title = meta.get("title") or n["title"]
            last = progress.get_last(slug)   # stored chapter index or None
            tracked_only = utils._is_tracked(slug) and not utils._has_chapters(slug)

            if tracked_only:
                sub = "Tracked · download to start"
                count = 0
            else:
                count = meta.get("chapters") or n["count"]
                sub = f"{count} chapters"
                if last is not None:
                    sub += f" · Last: Ch. {last + 1}"  # +1: index -> human number

            cover = os.path.join("novels", slug, meta["cover"]) if meta.get("cover") else ""

            row = _TapCard(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(124),
                padding="12dp",
                spacing="16dp",
                elevation=2,
                radius=theme.CARD_RADIUS,
            )

            cover_box = MDBoxLayout(
                size_hint=(None, 1), width=dp(62),
                radius=[10, 10, 10, 10], md_bg_color=theme.surface_color(),
            )
            if cover:
                cover_box.add_widget(FitImage(
                    source=cover, radius=theme.COVER_RADIUS, size_hint=(1, 1)))
            row.add_widget(cover_box)

            texts = MDBoxLayout(orientation="vertical", size_hint_y=1, spacing="2dp")
            texts.add_widget(MDLabel(
                text=title, bold=True,
                font_style="Subtitle1", size_hint_y=None, height="30dp"))
            texts.add_widget(MDLabel(
                text=sub, theme_text_color="Secondary",
                font_style="Caption", size_hint_y=None, height="18dp"))

            source = utils._get_source(slug)
            if source is not None and not tracked_only:
                texts.add_widget(MDLabel(
                    text=source.label, theme_text_color="Secondary",
                    font_style="Caption", size_hint_y=None, height="18dp"))

            if tracked_only:
                chip = MDBoxLayout(orientation="horizontal", adaptive_height=True,
                                   size_hint=(None, None), spacing="4dp")
                chip.add_widget(MDIcon(icon="bookmark", theme_text_color="Secondary"))
                chip.add_widget(MDLabel(
                    text="Tracked", theme_text_color="Secondary",
                    font_style="Caption", adaptive_height=True))
                row.add_widget(chip)
            elif last is not None and count:
                texts.add_widget(MDProgressBar(
                    value=last + 1, max=max(count, 1),
                    size_hint_y=None, height=dp(6)))

            row.add_widget(texts)
            row.on_release = lambda *_, s=slug, t=title, c=cover: \
                self._open_library_novel(s, t, c)
            self.library_list.add_widget(row)

    # ---------- library actions ----------

    def _open_library_novel(self, slug, title, cover):
        # Tap a library row -> the chapter list. Online chapters when
        # reachable (cached for speed); downloaded files as an offline fallback.
        source = utils._get_source(slug)
        raw_slug = slug.split(":", 1)[-1] if ":" in slug else slug
        utils._open_chapters_for(
            {"slug": raw_slug, "title": title or slug, "cover": cover},
            source,
            fallback=utils._local_chapters(slug),
        )