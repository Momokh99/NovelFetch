# pyright: reportGeneralTypeIssues=true
import asyncio
import math
import os

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogButtonContainer,
    MDDialogContentContainer,
    MDDialogHeadlineText,
    MDDialogSupportingText,
)
from kivymd.uix.fitimage import FitImage
from kivymd.uix.label import MDIcon, MDLabel
from kivymd.uix.list import MDList, MDListItem, MDListItemHeadlineText
from kivymd.uix.screen import MDScreen

from core.progress import LANGUAGES, progress
from gui.async_runner import async_loop
from gui.screens import (
    theme,
    utils,  # _get_source helper, meta
)
from gui.screens.app_settings import load_settings
from gui.screens.source_picker import open_source_picker
from gui.screens.utils import _snack

_GRID_COLS = {"large": 1, "medium": 2, "small": 3}
_CODE_TO_LABEL = {v: k for k, v in LANGUAGES.items()}


def _picker_options(chapters, seen, downloaded, lang):
    """Option rows for the batch download panel, mirroring DownloadPickerScreen:
    Original / Translated sections, each offering next 5/10/25, unread, all.

    *chapters* is the online chapter list, *seen* the read-index set, and
    *downloaded* the count of local files. Returns [{"label", "header"?,
    "subset", "translate"}] ready to render, or header-only row dicts."""
    label = _CODE_TO_LABEL.get(lang, lang)
    remaining = chapters[downloaded:]
    unread = [ch for i, ch in enumerate(chapters)
              if i not in seen and i >= downloaded]
    opts: list[dict] = []
    if remaining:
        opts.append({"label": "Original", "header": True})
        for n in (5, 10, 25):
            opts.append({"label": f"Next {len(remaining[:n])}",
                         "subset": remaining[:n], "translate": False})
        if unread:
            opts.append({"label": f"All unread ({len(unread)})",
                         "subset": unread, "translate": False})
        if chapters:
            opts.append({"label": f"All ({len(chapters)})",
                         "subset": list(chapters), "translate": False})
    if chapters:
        opts.append({"label": f"Translated ({label})", "header": True})
        for n in (5, 10, 25):
            subset = remaining[:n]
            if subset:
                opts.append({"label": f"Next {len(subset)}",
                             "subset": subset, "translate": True})
        if unread:
            opts.append({"label": f"All unread ({len(unread)})",
                         "subset": unread, "translate": True})
        if chapters:
            opts.append({"label": f"All ({len(chapters)})",
                         "subset": list(chapters), "translate": True})
    return opts


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


class SelectBadge(MDBoxLayout):
    """Selection visual on a library card: translucent accent tint over the
    cover plus a corner check circle. Takes the same zero-layout-space
    approach as UnreadBadge (size 0x0) so it never disturbs card layout."""

    selected = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (0, 0)
        self.bind(selected=self._redraw, parent=self._on_parent)
        self._redraw()

    def _on_parent(self, _widget, parent):
        if parent is not None:
            parent.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        if not self.selected or self.parent is None:
            return
        from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
        pw, ph = self.parent.width, self.parent.height
        if pw <= 0 or ph <= 0:
            return
        x = self.parent.x - self.x
        y = self.parent.y - self.y
        with self.canvas:
            # Full-cover accent tint.
            Color(theme.ACCENT[0], theme.ACCENT[1], theme.ACCENT[2], 0.22)
            RoundedRectangle(pos=(x, y), size=(pw, ph),
                             radius=theme.COVER_RADIUS)
            # Corner check circle (top-left, like Mihon).
            m = dp(3)
            pill = min(dp(22), ph - 2 * m)
            cx = x + m + pill / 2
            cy = y + ph - m - pill / 2
            Color(*theme.ACCENT)
            Ellipse(pos=(cx - pill / 2, cy - pill / 2), size=(pill, pill))
            # Anti-aliased-ish check via two wide lines.
            Color(1, 1, 1, 1)
            Line(points=[cx - pill * 0.2, cy,
                         cx - pill * 0.05, cy - pill * 0.15,
                         cx + pill * 0.25, cy + pill * 0.12],
                 width=dp(2.2), joint="round", cap="round")



class _TouchPassThrough(FloatLayout):
    """FloatLayout that lets touches fall through when hidden.

    A ``disabled`` widget in Kivy *consumes* touches on collision, which blocks
    the content below.  This subclass returns ``False`` when invisible so the
    library grid behind the overlay keeps working."""

    def on_touch_down(self, touch) -> bool | None:
        if self.opacity < 0.01:
            return False
        return super().on_touch_down(touch)

    def on_touch_move(self, touch) -> bool | None:
        if self.opacity < 0.01:
            return False
        return super().on_touch_move(touch)

    def on_touch_up(self, touch) -> bool | None:
        if self.opacity < 0.01:
            return False
        return super().on_touch_up(touch)


class _LongPressMixin(Widget):
    """Lets a card distinguish a hold (long-press) from a tap.

    A long-press is a still touch held ~0.45 s; any movement beyond the tap
    threshold (scrolling) cancels it. When it fires, ``_long_fired`` is set so
    the touching release does not double-trigger the ordinary on_release."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._lp_event = None
        self._lp_touch = None
        self._long_fired = False

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._lp_touch = touch
            self._lp_start_x = touch.x
            self._lp_start_y = touch.y
            self._lp_event = Clock.schedule_once(
                lambda dt: self._fire_long(touch), 0.45)
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch is self._lp_touch and self._lp_event is not None:
            dx = abs(touch.x - self._lp_start_x)
            dy = abs(touch.y - self._lp_start_y)
            if dx > dp(10) or dy > dp(10):
                self._cancel_long()
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch is self._lp_touch:
            self._lp_touch = None
            if self._lp_event is not None:
                self._lp_event.cancel()
                self._lp_event = None
            result = super().on_touch_up(touch)   # may fire on_release
            self._long_fired = False              # ...afterwards, reset
            return result
        return super().on_touch_up(touch)

    def _fire_long(self, touch):
        self._lp_event = None
        # Keep _lp_touch so the finger's eventual touch-up (which follows this
        # hold) can match and reset _long_fired; dropping it here would leave
        # the flag stuck True and swallow the *next* legitimate tap.
        self._long_fired = True
        on_long = getattr(self, "on_long_press", None)
        if on_long:
            on_long()

    def _cancel_long(self):
        if self._lp_event is not None:
            self._lp_event.cancel()
            self._lp_event = None
        self._lp_touch = None


class _SelectCard(_LongPressMixin, MDCard):
    """MDCard with long-press selection support (used by grid + row cards)."""


class HomeTab(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Widget tree lives in kv/home_tab.kv; alias the runtime-touched nodes.
        self.topbar = self.ids.topbar
        self.topbar.set_actions([("book-open-variant", open_source_picker)])
        self.content_box = self.ids.content_box
        self._lib_fp = None  # last _library_fingerprint() shown; skip rebuild
        # when nothing changed on disk.

        # ----- selection mode state -----
        self._select_mode = False
        self._selected: set[str] = set()
        self._library: list[dict] = []   # last entries passed to _build_library

        # ----- batch download state -----
        self._batch_active = False
        self._batch_descriptors: list[dict] = []
        self._batch_index = 0
        self._batch_lang = "ar"
        self._batch_lang_dialog = None
        self._batch_future = None
        self._batch_saved = 0
        self._batch_failed = 0
        self._batch_failed_novels = 0

        # Alias the selection footer + floating batch-panel nodes.
        self.sel_footer = self.ids.sel_footer
        self.sel_close = self.ids.sel_close
        self.sel_close.bind(on_release=lambda *_: self._exit_select())
        self.sel_count = self.ids.sel_count
        self.sel_download = self.ids.sel_download
        self.sel_download.bind(on_release=lambda *_: self._batch_download())
        self.sel_more = self.ids.sel_more
        self.sel_more.bind(on_release=lambda *_: self._open_selection_menu())

        self.batch_overlay = self.ids.batch_overlay
        self.batch_panel = self.ids.batch_panel
        self.ids.batch_close.bind(on_release=lambda *_: self._cancel_batch())
        self.ids.batch_cancel.bind(
            on_release=lambda *_: self._skip_current_download())
        self._set_panel_state("picking")

        # current_source is set in App.on_start(), AFTER build(). A zero-delay
        # Clock callback fires on the first frame — after on_start has run.
        Clock.schedule_once(lambda dt: self.refresh_library(), 0)

    # ---------- library ----------

    def refresh_library(self, force=False):
        # Run the disk scan on the async loop to avoid blocking the UI thread
        # when the library is large (os.listdir + meta reads).
        async def coro():
            from gui.screens import utils as u
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
        self._library = list(novels)   # keep for selection + batch titles
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
        app = MDApp.get_running_app()
        if app is None:
            return
        app.goto(
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

        card = _SelectCard(
            orientation="vertical", size_hint_y=None, adaptive_height=True,
            elevation=0, radius=[0] * 4, md_bg_color=[0, 0, 0, 0],
            padding=0, spacing="4dp")
        if cols:
            card.size_hint_x = 1.0 / cols
        else:
            card.size_hint_x = None
            card.width = dp(150)
        cbox = self._grid_cover(n, cols=cols, meta=meta)
        card.add_widget(cbox)
        badge = SelectBadge(selected=slug in self._selected)
        cbox.add_widget(badge)
        card._sel_badge = badge
        card._slug = slug
        card.add_widget(MDLabel(
            text=title, bold=True, font_style="Label", role="large", halign="center",
            size_hint_y=None, adaptive_height=True,
            shorten=True, shorten_from="right", max_lines=2))
        card.on_long_press = lambda *_, s=slug: self._enter_select(s)
        card.on_release = lambda *_, s=slug, t=title, c=cover: \
            self._card_release(card, s, t, c)
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
        cbox = self._cover_box(cover, cover_w)
        row.add_widget(cbox)
        badge = SelectBadge(selected=slug in self._selected)
        cbox.add_widget(badge)
        row._sel_badge = badge
        row._slug = slug

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
        row.on_long_press = lambda *_, s=slug: self._enter_select(s)
        row.on_release = lambda *_, s=slug, t=title, c=cover: \
            self._card_release(row, s, t, c)
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

    # ---------- selection mode ----------

    def _card_release(self, card, slug, title, cover):
        """Tap handler for selectable cards: opening a novel normally, but
        toggling selection while select mode is active. The long-press guard
        keeps the release right after a hold from toggling twice."""
        if getattr(card, "_long_fired", False):
            return
        if self._select_mode:
            self._toggle_select(slug)
        else:
            self._open_library_novel(slug, title, cover)

    def _enter_select(self, slug):
        """Long-press entry point: enter select mode (if needed) and select
        the pressed novel."""
        if self._batch_active:
            return
        if not self._select_mode:
            self._select_mode = True
            self._set_footer_visible(True)
        self._selected.add(slug)
        self._apply_selection_card(slug)
        self._update_footer()

    def _toggle_select(self, slug):
        if not self._select_mode:
            self._enter_select(slug)
            return
        if slug in self._selected:
            self._selected.discard(slug)
        else:
            self._selected.add(slug)
        self._apply_selection_card(slug)
        self._update_footer()

    def _exit_select(self):
        self._select_mode = False
        self._selected.clear()
        self._set_footer_visible(False)
        self._refresh_card_selection()

    def _leave_home_ui(self):
        """Called on navigation away from Home: close any modal state."""
        if self._batch_active:
            self._cancel_batch()
        else:
            self._exit_select()

    def _set_footer_visible(self, visible):
        self.sel_footer.height = "64dp" if visible else 0
        self.sel_footer.opacity = 1 if visible else 0
        self.sel_footer.disabled = not visible
        if visible:
            self._update_footer()

    def _update_footer(self):
        n = len(self._selected)
        self.sel_count.text = f"{n} selected"
        self.sel_download.disabled = n == 0
        self.sel_download.opacity = 0.4 if n == 0 else 1

    def _apply_selection_card(self, slug):
        for card in self.content_box.walk():
            if getattr(card, "_slug", None) == slug:
                badge = getattr(card, "_sel_badge", None)
                if badge is not None:
                    badge.selected = slug in self._selected

    def _refresh_card_selection(self):
        for card in self.content_box.walk():
            badge = getattr(card, "_sel_badge", None)
            slug = getattr(card, "_slug", "")
            if badge is not None:
                badge.selected = slug in self._selected

    # ---------- selection actions ----------

    def _selected_entries(self):
        by_slug = {n["slug"]: n for n in self._library}
        return [(slug, by_slug.get(slug, {})) for slug in sorted(self._selected)]

    def _batch_delete(self):
        dialog = getattr(self, "_confirm_dialog", None)
        if dialog is not None:
            dialog.dismiss()
        n = len(self._selected)
        if not n:
            return
        confirm = MDDialog(
            MDDialogHeadlineText(
                text=f"Delete {n} novel(s)?",
                halign="left",
            ),
            MDDialogSupportingText(
                text="The files will be removed but the novels stay tracked, "
                     "so you can re-download them later from Updates.",
                halign="left",
            ),
            MDDialogButtonContainer(
                MDButton(MDButtonText(text="Cancel"), style="text",
                         on_release=lambda *_: confirm.dismiss()),
                MDButton(MDButtonText(text="Delete"), style="text",
                         on_release=lambda *_: self._do_batch_delete(confirm)),
                spacing="8dp",
            ),
        )
        self._confirm_dialog = confirm
        confirm.open()

    def _do_batch_delete(self, dialog):
        dialog.dismiss()
        slugs = sorted(self._selected)
        for slug in slugs:
            utils._delete_library(slug)
        self._exit_select()
        self.refresh_library(force=True)

    def _batch_mark_read(self):
        for slug, entry in self._selected_entries():
            count = utils._read_meta(slug).get("chapters") or entry.get("count") or 0
            if count > 0:
                progress.mark_seen(slug, count - 1)
        self._after_progress_action()

    def _batch_mark_unread(self):
        for slug, _entry in self._selected_entries():
            progress.remove_history_entry(slug)
        self._after_progress_action()

    def _batch_track(self):
        for slug, entry in self._selected_entries():
            title = (utils._read_meta(slug).get("title")
                     or entry.get("title") or slug)
            progress.track(slug, title)
        self._after_progress_action()

    def _batch_untrack(self):
        for slug, _entry in self._selected_entries():
            progress.untrack(slug)
        self._after_progress_action()

    def _after_progress_action(self):
        progress.flush()
        self.refresh_library(force=True)

    def _open_selection_menu(self):
        dialog = getattr(self, "_selection_menu", None)
        if dialog is not None:
            dialog.dismiss()
        rows = MDList()
        items = [
            ("Mark read", self._batch_mark_read),
            ("Mark unread", self._batch_mark_unread),
            ("Track", self._batch_track),
            ("Untrack", self._batch_untrack),
        ]
        for label, handler in items:
            rows.add_widget(MDListItem(
                MDListItemHeadlineText(text=label),
                on_release=lambda *_, h=handler: self._run_selection_action(dialog, h)))
        rows.add_widget(MDListItem(
            MDListItemHeadlineText(text="Delete…"),
            on_release=lambda *_: self._batch_delete()))
        self._selection_menu = MDDialog(
            MDDialogHeadlineText(text="Selected novels", halign="left"),
            MDDialogContentContainer(rows),
        )
        self._selection_menu.open()

    def _run_selection_action(self, dialog, handler):
        if dialog is not None:
            dialog.dismiss()
        handler()

    # ---------- batch download ----------

    def _show_batch_overlay(self):
        self.batch_overlay.opacity = 1
        self._batch_active = True

    def _hide_batch_overlay(self):
        self.batch_overlay.opacity = 0
        self._batch_active = False

    def _batch_download(self):
        if not self._selected:
            return
        by_slug = {n["slug"]: n for n in self._library}
        self._batch_descriptors = []
        self._batch_index = 0
        self._batch_saved = 0
        self._batch_failed = 0
        self._batch_failed_novels = 0
        self.ids.batch_step.text = "Preparing"
        self.ids.batch_preparing.text = "Fetching chapter lists…"
        self._set_panel_state("preparing")
        self._show_batch_overlay()

        async def coro():
            sem = asyncio.Semaphore(4)

            async def one(slug):
                async with sem:
                    source = utils._get_source(slug)
                    if source is None or getattr(source, "blocked", False):
                        return None
                    raw = slug.split(":", 1)[-1] if ":" in slug else slug
                    try:
                        chapters = await utils._get_chapters(source, raw)
                    except Exception:
                        return None
                    if not chapters:
                        return None
                    entry = by_slug.get(slug, {})
                    title = (entry.get("title")
                             or utils._display_title(slug, slug))
                    return {"slug": slug, "title": title, "source": source,
                            "chapters": chapters, "total": len(chapters)}

            results = await asyncio.gather(*(one(s) for s in sorted(self._selected)))
            return [r for r in results if r]

        async_loop.run(coro(), self._on_batch_prep_done, timeout=180)

    def _on_batch_prep_done(self, results, error):
        if error is not None or not results:
            self._reset_batch()
            self._hide_batch_overlay()
            _snack("Could not fetch chapter data. Check your connection.")
            return
        self._batch_descriptors = results
        self._show_picker()

    def _reset_batch(self):
        self._batch_descriptors = []
        self._batch_index = 0
        self._batch_saved = 0
        self._batch_failed = 0
        self._batch_failed_novels = 0
        if self._batch_future is not None and not self._batch_future.done():
            self._batch_future.cancel()
        self._batch_future = None

    def _skip_current_download(self):
        """Cancel the in-flight download for the current novel and move on."""
        if self._batch_future is not None and not self._batch_future.done():
            self._batch_future.cancel()
        self._batch_failed_novels += 1
        self._advance_batch()

    def _cancel_batch(self):
        self._reset_batch()
        self._hide_batch_overlay()
        _snack("Batch cancelled")
        self.refresh_library(force=True)

    def _show_picker(self):
        if self._batch_index >= len(self._batch_descriptors):
            self._finish_batch()
            return
        desc = self._batch_descriptors[self._batch_index]
        self.ids.batch_step.text = (
            f"Download · {self._batch_index + 1}/{len(self._batch_descriptors)}")
        self.ids.batch_title.text = desc["title"]
        local = len(utils._local_chapters(desc["slug"]))
        seen = progress.get_seen(desc["slug"])
        unread = [ch for i, ch in enumerate(desc["chapters"])
                  if i not in seen and i >= local]
        self.ids.batch_summary.text = (
            f"{local} downloaded  |  {len(unread)} unread  |  "
            f"{desc['total']} total")
        self.ids.batch_lang_label.text = _CODE_TO_LABEL.get(
            self._batch_lang, self._batch_lang)
        opts = _picker_options(desc["chapters"], seen, local, self._batch_lang)
        self.ids.batch_options.clear_widgets()
        for o in opts:
            if o.get("header"):
                self.ids.batch_options.add_widget(self._picker_header(o["label"]))
            else:
                item = MDListItem(
                    MDListItemHeadlineText(text=o["label"]),
                    on_release=lambda *_, op=o: self._start_download(desc, op))
                self.ids.batch_options.add_widget(item)
        self._set_panel_state("picker")

    @staticmethod
    def _picker_header(text):
        return MDLabel(
            text=text, bold=True, theme_text_color="Secondary",
            font_style="Label", role="medium",
            size_hint_y=None, height=dp(32), padding=(dp(8), dp(8)))

    def _pick_batch_language(self):
        rows = MDList()
        for label, code in LANGUAGES.items():
            rows.add_widget(MDListItem(
                MDListItemHeadlineText(text=label),
                on_release=lambda *_, c=code, lbl=label: self._set_batch_lang(c, lbl)))
        self._batch_lang_dialog = MDDialog(
            MDDialogHeadlineText(text="Translate to", halign="left"),
            MDDialogContentContainer(rows),
        )
        self._batch_lang_dialog.open()

    def _set_batch_lang(self, code, _label):
        if self._batch_lang_dialog is not None:
            self._batch_lang_dialog.dismiss()
        self._batch_lang = code
        self._show_picker()

    def _start_download(self, desc, option):
        subset = list(option.get("subset") or [])
        translate = bool(option.get("translate"))
        if not subset:
            self._advance_batch()
            return
        self.ids.batch_bar.max = max(len(subset), 1)
        self.ids.batch_bar.value = 0
        self.ids.batch_status.text = (
            f"0/{len(subset)} — 0 saved"
            + (" (translated)" if translate else ""))
        self._set_panel_state("progress")

        async def coro():
            return await utils._download_novel(
                desc["source"], desc["slug"], subset, desc["title"],
                total=desc["total"], progress_cb=self._on_batch_progress,
                translate=translate, lang=self._batch_lang)

        self._batch_future = async_loop.run(
            coro(), lambda r, e: self._on_novel_done(desc, r, e))

    def _on_batch_progress(self, done, saved):
        Clock.schedule_once(lambda dt: self._set_batch_progress(done, saved))

    def _set_batch_progress(self, done, saved):
        self.ids.batch_bar.value = min(done, self.ids.batch_bar.max)
        self.ids.batch_status.text = (
            f"{done}/{int(self.ids.batch_bar.max)} — {saved} saved")

    def _on_novel_done(self, desc, result, error):
        if error is not None:
            saved = failed = 0
            self._batch_failed_novels += 1
        else:
            saved, failed = result
            if saved == 0 and failed > 0:
                self._batch_failed_novels += 1
        self._batch_saved += saved
        self._batch_failed += failed
        self._advance_batch()

    def _advance_batch(self):
        self._batch_index += 1
        if self._batch_index < len(self._batch_descriptors):
            self._show_picker()
        else:
            self._finish_batch()

    def _finish_batch(self):
        self._hide_batch_overlay()
        total = len(self._batch_descriptors)
        text = f"Downloaded {self._batch_saved} chapter(s) from {total} novel(s)"
        if self._batch_failed:
            text += f" · {self._batch_failed} failed"
        self._reset_batch()
        _snack(text)
        self.refresh_library(force=True)

    def _set_panel_state(self, state):
        """Switch the floating panel's body between the three working states:
        'preparing' (fetching chapter lists), 'picker' (choose subset), and
        'progress' (downloading the current novel)."""
        preparing = state == "preparing"
        picking = state == "picker"
        progressing = state == "progress"
        self.ids.batch_preparing.opacity = 1 if preparing else 0
        self.ids.batch_options_scroll.opacity = 1 if picking else 0
        self.ids.batch_options_scroll.disabled = not picking
        self.ids.batch_summary.opacity = 1 if picking else 0
        self.ids.batch_lang_row.opacity = 1 if picking else 0
        self.ids.batch_progress_box.opacity = 1 if progressing else 0
        self.ids.batch_progress_box.disabled = not progressing
