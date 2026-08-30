import math
import os

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scrollview import ScrollView

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.fitimage import FitImage
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.screen import MDScreen

from progress import progress
from async_runner import async_loop
from screens import utils                    # _get_source helper, meta
from screens import theme
from screens.app_settings import load_settings
from screens.source_picker import open_source_picker

_GRID_COLS = {"large": 1, "medium": 2, "small": 3}


def _count_summary(total, tracked):
    """'3 novels · 2 tracked' caption text from plain numbers."""
    text = f"{total} novel{'s' if total != 1 else ''}"
    if tracked:
        text += f" · {tracked} tracked"
    return text


def _grid_cols():
    return _GRID_COLS.get(load_settings().get("card_grid_size", "medium"), 2)


def _unread_count(count, last):
    """Unread chapters: total minus read. *last* is the 0-based index of the
    last read chapter, or None when nothing has been read."""
    if last is None:
        return count
    return max(0, count - (last + 1))


def _badge_text(count):
    """Badge label: the count, clamped like Mihon's '999+' caps."""
    return "999+" if count > 999 else str(count)


class _TapFriendlyHScroll(ScrollView):
    """Horizontal scroll whose child buttons still receive taps even when the
    finger is pressed and held still.

    ScrollView classifies a still press as a scroll once ``scroll_timeout``
    elapses (default 250 ms) and silently swallows the tap on release. Here
    real scrolling is detected by movement > ``scroll_distance`` instead.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scroll_timeout = 1_000_000

    def on_scroll_stop(self, touch, check_children=True):
        uid = self._get_uid()
        ud = touch.ud.get(uid)
        if ud:
            dx = ud.get("dx", 0) or 0
            dy = ud.get("dy", 0) or 0
            if (ud.get("mode") == "scroll"
                    and dx < self.scroll_distance
                    and dy < self.scroll_distance):
                ud["mode"] = "unknown"
        return super().on_scroll_stop(touch, check_children=check_children)


class _FitCover(FitImage):
    """FitImage variant that stretches the image to fill the box while
    keeping rounded-corner clipping via the stencil."""

    def _late_init(self, *args):
        self._container = Image(
            source=self.source, mipmap=self.mipmap,
            size_hint=(1, 1), allow_stretch=True, keep_ratio=False)
        self.bind(source=self._container.setter("source"))
        self.add_widget(self._container)


class UnreadBadge(MDBoxLayout):
    """Mihon-style unread-count pill floating on a cover corner.

    The widget takes no layout space (zero size) so it can sit next to the
    cover without an overlay layout; it draws itself onto the parent cover
    box's corner via canvas instructions.
    """

    count = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from kivy.core.text import Label as CoreLabel
        self._label = CoreLabel(text="", font_size=dp(10), bold=True)
        self.size_hint = (None, None)
        self.size = (0, 0)
        self.bind(count=self._redraw, parent=self._on_parent)
        self._redraw()

    def _on_parent(self, _widget, parent):
        if parent is not None:
            parent.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def _redraw(self, *_):
        from kivy.graphics import Color, Rectangle, RoundedRectangle
        self.canvas.clear()
        n = int(self.count)
        self._label.text = _badge_text(n) if n else ""
        if not n or self.parent is None:
            return
        pw, ph = self.parent.width, self.parent.height
        if pw <= 0 or ph <= 0:
            return
        app = MDApp.get_running_app()
        if app is None:
            prim = (0.13, 0.55, 0.96, 1)
        else:
            prim = list(app.theme_cls.primaryColor)
        m = dp(2.5)  # inner padding floats the pill off the corner
        pill = min(dp(22), ph - 2 * m)
        x = self.parent.x - self.x + pw - m - pill
        y = self.parent.y - self.y + m
        with self.canvas:
            Color(*prim)
            RoundedRectangle(pos=(x, y), size=(pill, pill),
                             radius=[pill / 2] * 4)
            self._label.refresh()
            tex = self._label.texture
            if tex:
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, pos=(x, y), size=(pill, pill))


class ReadIndicator(MDBoxLayout):
    """Compact reading-progress indicator drawn with canvas instructions."""

    style = StringProperty("off")
    frac = NumericProperty(0.0)
    display_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._label = MDLabel(
            halign="left", valign="middle", font_style="Label", role="medium",
            bold=True, font_size=sp(10), theme_text_color="Secondary")
        self.add_widget(self._label)
        self.bind(
            size=self._redraw, style=self._redraw,
            frac=self._redraw, display_text=self._redraw)
        self._redraw()

    def _track(self):
        return (0.55, 0.55, 0.6, 0.15)

    def _redraw(self, *_):
        self.canvas.clear()
        style = self.style
        if style == "off":
            self._label.text = ""
            return
        app = MDApp.get_running_app()
        if app is None:
            prim = (0.13, 0.55, 0.96, 1)
        else:
            prim = list(app.theme_cls.primaryColor)
        w, h = self.width, self.height
        if w <= 0 or h <= 0:
            return
        frac = max(0.0, min(1.0, self.frac))
        if style == "text":
            self._label.text = self.display_text
            return
        self._label.text = ("" if style != "percentage"
                            else f"{int(round(frac * 100))}%")
        if style != "percentage":
            self._label.halign = "left"
        from kivy.graphics import Color, Ellipse, RoundedRectangle
        with self.canvas:
            if style == "linear":
                r = h / 2
                Color(*self._track())
                RoundedRectangle(pos=self.pos, size=(w, h), radius=[r] * 4)
                if frac > 0:
                    Color(*prim)
                    RoundedRectangle(pos=self.pos, size=(w * frac, h),
                                     radius=[r] * 4)
            elif style == "percentage":
                self._label.halign = "center"
            elif style in ("blocks", "dots"):
                n = 12
                gap = dp(2)
                cw = (w - gap * (n - 1)) / n
                filled = int(round(frac * n))
                for i in range(n):
                    x = self.x + i * (cw + gap)
                    if i < filled:
                        Color(*prim)
                    else:
                        Color(*self._track())
                    if style == "blocks":
                        RoundedRectangle(pos=(x, self.y), size=(cw, h),
                                         radius=[dp(1.5)] * 4)
                    else:
                        d = max(1.0, min(cw, h) - dp(1))
                        Ellipse(pos=(x + (cw - d) / 2, self.y + (h - d) / 2),
                                size=(d, d))
            elif style == "wave":
                amp = dp(1.5)
                base = h * (1 - frac)
                col_w = 4.0
                x = self.x
                while x < self.x + w:
                    t = (x - self.x) / w
                    top = base + amp * math.sin(t * 4 * math.pi)
                    Color(prim[0], prim[1], prim[2], 0.4)
                    RoundedRectangle(pos=(x, self.y + top),
                                     size=(col_w, h - top), radius=[0] * 4)
                    x += col_w


class HomeTab(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Widget tree lives in kv/home_tab.kv; alias the runtime-touched nodes.
        self.topbar = self.ids.topbar
        self.topbar.set_actions([("book-open-variant", open_source_picker)])
        self.content_box = self.ids.content_box
        self._lib_fp = None  # last _library_fingerprint() shown; skip rebuild
        # when nothing changed on disk.

        # current_source is set in App.on_start(), AFTER build(). A zero-delay
        # Clock callback fires on the first frame — after on_start has run.
        Clock.schedule_once(lambda dt: self.refresh_library(), 0)

    # ---------- library ----------

    def refresh_library(self, force=False):
        # Run the disk scan on the async loop to avoid blocking the UI thread
        # when the library is large (os.listdir + meta reads).
        async def coro():
            from screens import utils as u
            return u._library_entries_and_fingerprint()

        def on_done(payload, error):
            if error is not None:
                import traceback
                traceback.print_exception(type(error), error, error.__traceback__)
                return
            novels, fp = payload
            if not force and fp == self._lib_fp:
                # Nothing on disk changed since the last refresh: keep the
                # current widget tree instead of rebuilding everything.
                return
            self._lib_fp = fp
            try:
                self._build_library(novels)
            except Exception:
                import traceback
                traceback.print_exc()

        async_loop.run(coro(), on_done, timeout=10)

    def _build_library(self, novels):
        box = self.content_box
        box.clear_widgets()
        self.topbar.set_title(
            f"NovelFetch · {len(novels)}" if novels else "NovelFetch")
        if not novels:
            box.add_widget(self._empty_state())
            return
        layout = load_settings().get("home_layout", "A")
        builder = getattr(self, f"_layout_{layout}", self._layout_A)
        try:
            builder(novels)
        except Exception:
            # A single bad card shouldn't blank the whole library.
            import traceback
            traceback.print_exc()
            box.clear_widgets()
            for n in novels:
                try:
                    box.add_widget(self._row_card(n))
                except Exception:
                    import traceback
                    traceback.print_exc()

    # ---------- section primitives ----------

    def _section_header(self, text):
        return MDLabel(
            text=text, bold=True, adaptive_height=True,
            size_hint_y=None, padding=(0, dp(4), 0, dp(2)))

    def _count_label(self, novels):
        n_tracked = sum(
            1 for n in novels
            if utils._is_tracked(n["slug"]) and not utils._has_chapters(n["slug"])
        )
        return MDLabel(
            text=_count_summary(len(novels), n_tracked),
            theme_text_color="Secondary",
            font_style="Label", role="large", adaptive_height=True, size_hint_y=None)

    def _empty_state(self):
        box = MDBoxLayout(
            orientation="vertical", adaptive_height=True,
            padding="16dp", spacing="4dp")
        box.add_widget(MDIcon(
            icon="bookshelf", halign="center", font_size="56dp",
            theme_text_color="Secondary"))
        box.add_widget(MDLabel(
            text="Your library is empty", halign="center", bold=True,
            adaptive_height=True))
        box.add_widget(MDLabel(
            text="Browse the hot list or search for novels\nto start reading.",
            halign="center", theme_text_color="Secondary",
            font_style="Label", role="large", adaptive_height=True))
        return box

    def _cover_box(self, cover, width, radius=None, flex_h=None):
        radius = radius or theme.COVER_RADIUS
        box = MDBoxLayout(
            size_hint=(None, 1), width=width,
            radius=radius, md_bg_color=theme.surface_color())
        if cover:
            box.add_widget(_FitCover(
                source=cover, radius=radius, size_hint=(1, 1)))
        return box

    def _card_grid(self, novels, cols):
        grid = MDBoxLayout(
            orientation="vertical", adaptive_height=True, spacing="8dp")
        for i in range(0, len(novels), cols):
            row = MDBoxLayout(
                orientation="horizontal", adaptive_height=True, spacing="8dp")
            for n in novels[i:i + cols]:
                try:
                    row.add_widget(self._grid_card(n, cols=cols))
                except Exception:
                    import traceback
                    traceback.print_exc()
            if row.children:
                grid.add_widget(row)
        return grid

    def _hscroll(self, novels):
        """Horizontal scroll of cover cards (Continue Reading section)."""
        card_w = dp(150)
        gap = dp(8)
        row = MDBoxLayout(
            orientation="horizontal", adaptive_height=True,
            size_hint_x=None, spacing=gap,
            padding=(gap, 0, gap, 0))
        row.width = len(novels) * card_w + max(len(novels) - 1, 0) * gap + gap * 2
        for n in novels:
            try:
                row.add_widget(self._continue_card(n))
            except Exception:
                import traceback
                traceback.print_exc()
        sv = _TapFriendlyHScroll(
            size_hint_y=None, height="270dp",
            do_scroll_x=True, do_scroll_y=False,
            bar_width=0, scroll_type=["content"])
        sv.add_widget(row)
        return sv

    # ---------- shared card builders ----------

    def _continue_card(self, n, width=dp(150), cover_frac=1.0, cols=0):
        slug = n["slug"]
        meta = utils._read_meta(slug)
        title = meta.get("title") or n["title"]
        last = progress.get_last(slug)
        count = meta.get("chapters") or n["count"]
        cover = os.path.join("novels", slug, meta["cover"]) if meta.get("cover") else ""

        card = MDCard(
            orientation="vertical", size_hint_y=None,
            height="260dp" if cover_frac >= 1 else "190dp",
            elevation=2, radius=theme.CARD_RADIUS,
            padding="8dp", spacing="4dp",
        )
        if cols:
            card.size_hint_x = 1.0 / cols
        else:
            card.size_hint_x = None
            card.width = width

        cover_h = 1.0 if cover_frac >= 1 else 0.72
        cbox = MDBoxLayout(
            size_hint=(1, cover_h),
            radius=theme.COVER_RADIUS, md_bg_color=theme.surface_color())
        if cover:
            cbox.add_widget(_FitCover(
                source=cover, radius=theme.COVER_RADIUS, size_hint=(1, 1)))
        unread = _unread_count(count, last)
        if unread:
            cbox.add_widget(UnreadBadge(count=unread))
        card.add_widget(cbox)

        card.add_widget(MDLabel(
            text=title, bold=True, font_style="Label", role="large",
            size_hint_y=None, height="22dp", halign="center",
            shorten=True, shorten_from="right", max_lines=1))
        sub = ""
        if last is not None:
            sub = f"Ch. {last + 1}/{count if count else '?'}"
        card.add_widget(MDLabel(
            text=sub, theme_text_color="Secondary",
            font_style="Label", role="large", size_hint_y=None, height="18dp",
            halign="center"))

        card.on_release = lambda *_, s=slug, t=title, c=cover, l=last: \
            self._resume_novel(s, t, c, l)
        return card

    def _resume_novel(self, slug, title, cover, last):
        """Continue Reading tap: jump straight into the reader at the
        last-read chapter.

        Downloaded novels open instantly from local files; novels that were
        read online fall back to a cached online chapter list (the reader
        loads whichever is available: translated → English → network). The
        chapter list opens only when nothing usable is found."""
        chapters = utils._local_chapters(slug)
        if chapters and last is not None and 0 <= last < len(chapters):
            self._goto_reader(slug, title, chapters, last)
            return
        source = utils._get_source(slug)
        if source is None or getattr(source, "blocked", False):
            self._open_library_novel(slug, title, cover)
            return
        raw = slug.split(":", 1)[-1] if ":" in slug else slug

        async def coro():
            try:
                return await utils._get_chapters(source, raw)
            except Exception:
                return None

        def on_done(chapters, error):
            if (error is None and chapters
                    and last is not None and 0 <= last < len(chapters)):
                self._goto_reader(slug, title, chapters, last)
                return
            self._open_library_novel(slug, title, cover)

        async_loop.run(coro(), on_done, timeout=30)

    def _goto_reader(self, slug, title, chapters, start):
        MDApp.get_running_app().goto(
            "reader",
            chapters=chapters,
            slug=slug,
            source=utils._get_source(slug),
            title=title or slug,
            start=start,
        )

    def _grid_cover(self, n, cols=2, height=260, meta=None):
        """Mihon-style library cover: a bare rounded image (no card chrome)
        with an unread-count badge in the corner. Fixed height per grid
        column so grid tiles stack reliably at any screen size."""
        slug = n["slug"]
        if meta is None:
            meta = utils._read_meta(slug)
        cover = os.path.join("novels", slug, meta["cover"]) if meta.get("cover") else ""
        count = meta.get("chapters") or n["count"]
        last = progress.get_last(slug)
        if cols <= 1:
            height = 320
        elif cols >= 3:
            height = 230

        cbox = MDBoxLayout(
            size_hint=(1, None), height="%ddp" % height,
            radius=theme.COVER_RADIUS, md_bg_color=theme.surface_color())
        if cover:
            cbox.add_widget(_FitCover(
                source=cover, radius=theme.COVER_RADIUS, size_hint=(1, 1)))
        unread = _unread_count(count, last)
        if unread:
            cbox.add_widget(UnreadBadge(count=unread))
        return cbox

    def _grid_card(self, n, cols=0):
        """Bare-cover grid tile: cover with centered title below (no elevation,
        no card box — the Mihon comfortable-grid look)."""
        slug = n["slug"]
        meta = utils._read_meta(slug)
        title = meta.get("title") or n["title"]
        cover = os.path.join("novels", slug, meta["cover"]) if meta.get("cover") else ""

        card = MDCard(
            orientation="vertical", size_hint_y=None, adaptive_height=True,
            elevation=0, radius=[0] * 4, md_bg_color=[0, 0, 0, 0],
            padding=0, spacing="4dp")
        if cols:
            card.size_hint_x = 1.0 / cols
        else:
            card.size_hint_x = None
            card.width = dp(150)
        card.add_widget(self._grid_cover(n, cols=cols, meta=meta))
        card.add_widget(MDLabel(
            text=title, bold=True, font_style="Label", role="large", halign="center",
            size_hint_y=None, adaptive_height=True,
            shorten=True, shorten_from="right", max_lines=2))
        card.on_release = lambda *_, s=slug, t=title, c=cover: \
            self._open_library_novel(s, t, c)
        return card

    def _row_card(self, n, compact=False, badge=False):
        slug = n["slug"]
        meta = utils._read_meta(slug)
        title = meta.get("title") or n["title"]
        last = progress.get_last(slug)
        # Reuse the already-fetched meta instead of utils._is_tracked(slug),
        # which would re-read meta.json from disk.
        tracked_only = ((bool(meta.get("tracked")) or progress.is_tracked(slug))
                        and not utils._has_chapters(slug))

        if tracked_only:
            sub = "Tracked · download to start"
            count = 0
        else:
            count = meta.get("chapters") or n["count"]
            sub = f"{count} chapters"
            if last is not None:
                sub += f" · Last: Ch. {last + 1}"  # +1: index -> human number

        cover = os.path.join("novels", slug, meta["cover"]) if meta.get("cover") else ""

        height = dp(92) if compact else dp(124)
        row = MDCard(
            orientation="horizontal",
            size_hint_y=None, height=height,
            padding="12dp", spacing="16dp",
            elevation=2, radius=theme.CARD_RADIUS,
        )

        cover_w = dp(48) if compact else dp(62)
        row.add_widget(self._cover_box(cover, cover_w))

        texts = MDBoxLayout(orientation="vertical", size_hint_y=None, adaptive_height=True, spacing="2dp",
                            pos_hint={"center_x": 0.5, "center_y": 0.5})
        title_h = "26dp" if compact else "30dp"
        texts.add_widget(MDLabel(
            text=title, bold=True,
            font_style="Title", role="small",
            size_hint_y=None, height=title_h,
            shorten=True, shorten_from="right", max_lines=1,
            valign="top"))
        texts.add_widget(MDLabel(
            text=sub, theme_text_color="Secondary",
            font_style="Label", role="large", size_hint_y=None, height="20dp",
            valign="top"))

        source = utils._get_source(slug)
        if source is not None and not tracked_only:
            if badge:
                source_label = MDLabel(
                    text=source.label, theme_text_color="Secondary",
                    font_style="Label", role="large", size_hint_y=None, height="20dp",
                    valign="top")
                source_label.halign = "left"
                texts.add_widget(source_label)
            else:
                texts.add_widget(MDLabel(
                    text=source.label, theme_text_color="Secondary",
                    font_style="Label", role="large", size_hint_y=None, height="20dp",
                    valign="top"))

        if tracked_only:
            chip = MDBoxLayout(
                orientation="horizontal", adaptive_height=True,
                size_hint=(None, None), spacing="4dp")
            chip.add_widget(MDIcon(icon="bookmark", theme_text_color="Secondary"))
            chip.add_widget(MDLabel(
                text="Tracked", theme_text_color="Secondary",
                font_style="Label", role="medium", adaptive_height=True))
            row.add_widget(chip)
        elif last is not None and count:
            style = load_settings().get("read_indicator", "off")
            if style != "off":
                # text/percentage render a label, so give those styles the
                # vertical room; the canvas bar styles stay a thin strip.
                ind_h = dp(22) if style in ("text", "percentage") else dp(6)
                try:
                    texts.add_widget(ReadIndicator(
                        frac=(last + 1) / max(count, 1), style=style,
                        display_text=f"Ch. {last + 1}/{count}",
                        size_hint_y=None, height=ind_h))
                except Exception:
                    import traceback
                    traceback.print_exc()

        texts_rl = RelativeLayout(size_hint=(1, 1))
        texts_rl.add_widget(texts)
        row.add_widget(texts_rl)
        row.on_release = lambda *_, s=slug, t=title, c=cover: \
            self._open_library_novel(s, t, c)
        return row

    # ---------- layout builders ----------

    def _continue_list(self, novels):
        """Library novels with reading progress, newest-read first (driven
        by each novel's last-read timestamp, not library order)."""
        by_slug = {n["slug"]: n for n in novels}
        cont = [by_slug.pop(h["slug"]) for h in progress.get_history()
                if h["slug"] in by_slug]
        # Novels with progress but no read timestamp (legacy) trail the list.
        cont += [n for n in novels
                 if n["slug"] in by_slug
                 and progress.get_last(n["slug"]) is not None]
        return cont[:10]

    def _continue_section(self, cont):
        """Continue Reading: hscroll of cover cards, or an empty-state note."""
        sec = MDBoxLayout(
            orientation="vertical", adaptive_height=True,
            spacing=theme.SECTION_GAP)
        sec.add_widget(self._section_header("Continue Reading"))
        if cont:
            sec.add_widget(self._hscroll(cont))
        else:
            sec.add_widget(MDLabel(
                text="Nothing in progress yet.",
                theme_text_color="Secondary", font_style="Label", role="large",
                adaptive_height=True, size_hint_y=None))
        return sec

    def _layout_A(self, novels):
        """Continue-Reading hscroll + library cover-card grid."""
        box = self.content_box
        cont = self._continue_list(novels)
        if load_settings().get("show_continue_reading", True):
            box.add_widget(self._continue_section(cont))
        box.add_widget(self._section_header("My Library"))
        box.add_widget(self._count_label(novels))
        box.add_widget(self._card_grid(novels, _grid_cols()))

    def _layout_B(self, novels):
        """Continue-Reading hscroll + source-badge compact rows."""
        box = self.content_box
        cont = self._continue_list(novels)
        if load_settings().get("show_continue_reading", True):
            box.add_widget(self._continue_section(cont))
        box.add_widget(self._section_header("My Library"))
        box.add_widget(self._count_label(novels))
        for n in novels:
            box.add_widget(self._row_card(n, compact=True, badge=True))

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