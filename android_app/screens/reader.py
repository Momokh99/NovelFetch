import asyncio
import os
import re

from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel

from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar

from progress import LANGUAGES, progress
from async_runner import async_loop
from screens import utils, theme
from translation import _translate_text

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _HAS_ARABIC_SHAPING = True
except ImportError:
    _HAS_ARABIC_SHAPING = False

_ARABIC_FONT = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "NotoNaskhArabic.ttf"
)

# Invisible RTL/LTR marks and embedding controls injected by Google
# Translate.  Stripped before display so they don't render as tofu boxes.
_CTRL_CHARS_RE = re.compile(
    "[\u200e\u200f"
    "\u202a\u202b\u202c\u202d\u202e"
    "\u2066\u2067\u2068\u2069\u206a\u206b\u206c\u206d"
    "\ufeff"
    "\u061c]"  # Arabic Letter Mark
)


def _strip_control_chars(text):
    """Remove invisible bidi/RTL control characters that cause tofu boxes."""
    return _CTRL_CHARS_RE.sub("", text)


def _shape_arabic_text(text):
    if not _HAS_ARABIC_SHAPING:
        return _strip_control_chars(text)
    text = _strip_control_chars(text)
    reshaped = arabic_reshaper.reshape(text)
    return _strip_control_chars(get_display(reshaped, base_dir="R"))


def _greedy_wrap(widths, space_w, avail):
    """Greedy word-wrap on pre-measured widths.

    widths -- list of word widths in px
    space_w -- width of a single space
    avail  -- usable line width
    Returns a list of lines, each a list of word indices.
    """
    lines = []
    cur = []
    cur_w = 0
    for i, w in enumerate(widths):
        extra = w if not cur else w + space_w
        if cur and cur_w + extra > avail:
            lines.append(cur)
            cur = [i]
            cur_w = w
        else:
            cur.append(i)
            cur_w += extra
    if cur:
        lines.append(cur)
    return lines


def _wrap_rtl_lines(reshaped_text, measure, space_w, avail):
    """Split reshaped logical text into lines that fit `avail` px.

    measure(word) -> px width.  Returns a list of logical-order lines
    (bidi-flipping is done by the caller, per line).
    """
    out = []
    for para in reshaped_text.split("\n"):
        words = para.split()
        if not words:
            out.append("")
            continue
        widths = [measure(w) for w in words]
        for line_idx in _greedy_wrap(widths, space_w, avail):
            out.append(" ".join(words[j] for j in line_idx))
    return out


# A single Kivy Label renders into ONE OpenGL texture and GPUs cap
# texture size (4096-16384px depending on device).  A full chapter
# wrapped into one label exceeds that and renders black, so text is
# split into stacked chunk labels whose textures stay below this.
_MAX_CHUNK_PX = 2500


def lines_per_chunk(line_h, cap=_MAX_CHUNK_PX):
    """Lines per chunk so one chunk's texture stays <= cap px tall."""
    if line_h <= 0:
        return 1
    return max(1, int(cap // line_h))


def pack_lines_into_chunks(lines, per_chunk):
    """Join display lines into strings of at most per_chunk lines each."""
    if per_chunk < 1:
        per_chunk = 1
    return ["\n".join(lines[i:i + per_chunk])
            for i in range(0, len(lines), per_chunk)]


class ReaderScreen(MDScreen):
    """Read chapters local-first (downloaded files), falling back to the
    source's read_chapter() over the network. Prev/next, translate/revert,
    and A-/A+ font size controls.

    When meta.json specifies a "lang", a translated chapter file
    ({title}_{lang}.txt) takes priority over the English file.  The
    translate button swaps between the two local copies instantly (no
    network); online translation is only used when no local copy exists."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chapters = []
        self.slug = ""
        self.source = None
        self.current = 0
        self._original_text = ""
        self._translated_text = ""
        self._lang = None
        self._offline_lang = None
        self._offline_en_path = ""
        self._offline_tr_path = ""
        self._busy = False
        self._lang_dialog = None
        self._raw_text = ""
        self._shown_lang = None
        self._disp_key = None
        self._font_event = None
        self._meas_cache = {}

        from screens.app_settings import load_settings
        self._font_size = load_settings()["reader_font_size"]

        self.header = self.ids.header
        self.header.on_back = self._back
        self.title_label = self.header.ids.title_label

        self.scroll = self.ids.scroll
        self.body_box = self.ids.body_box
        self.body_box.bind(width=lambda *_: self._reflow())

        self.prev_btn = self.ids.prev_btn
        self.prev_btn.bind(on_release=lambda *_: self._prev())
        self.next_btn = self.ids.next_btn
        self.next_btn.bind(on_release=lambda *_: self._next())
        self.font_down_btn = self.ids.font_down_btn
        self.font_down_btn.bind(on_release=lambda *_: self._font(-2))
        self.font_up_btn = self.ids.font_up_btn
        self.font_up_btn.bind(on_release=lambda *_: self._font(2))
        self.translate_btn = self.ids.translate_btn
        self.translate_btn.bind(on_release=lambda *_: self._toggle_translate())
        self.font_size_label = self.ids.font_size_label
        self.font_size_label.text = str(self._font_size)
        self.counter = self.ids.counter

        self.bottom_bar = self.ids.bottom_bar
        self.bottom_divider = self.ids.bottom_divider
        self.bottom_divider.md_bg_color = theme.DIVIDER

    # ---------- translate toggle ----------

    def _toggle_translate(self):
        if self._busy:
            return
        if self._translated_text:
            # Currently showing translated → revert to English
            self._revert()
        elif self._offline_en_path and self._offline_tr_path:
            # Both offline copies exist → swap between them
            self._swap_offline()
        elif self._offline_en_path:
            # Only English file on disk → open language picker for online
            self._pick_language()
        else:
            self._pick_language()

    def _swap_offline(self):
        """Swap between translated and English local files."""
        if self._offline_lang:
            # Currently showing translated → swap to English
            try:
                with open(self._offline_en_path, encoding="utf-8") as f:
                    content = f.read()
                self._translated_text = ""
                self._offline_lang = None
                self._lang = None
                self.translate_btn.icon = "translate"
                self._show_text(content)
            except Exception:
                self._notify("Could not read English copy.")
        else:
            # Currently showing English → swap to translated
            try:
                with open(self._offline_tr_path, encoding="utf-8") as f:
                    content = f.read()
                meta_lang = utils._meta_lang(self.slug) \
                    if self.slug else None
                self._translated_text = content
                self._offline_lang = meta_lang
                self._lang = meta_lang
                self.translate_btn.icon = "undo-variant"
                self._show_text(content, lang=meta_lang)
            except Exception:
                self._notify("Could not read translated copy.")

    # ---------- goto() contract ----------

    def load(self, chapters=None, slug="", source=None, title="Reader",
             start=0, **kwargs):
        self._set_busy(False)
        self._translated_text = ""
        self._lang = None
        self._offline_lang = None
        self.slug = slug
        self.source = source
        self.chapters = chapters if chapters is not None else \
            utils._local_chapters(slug)
        if not self.chapters:
            self._show_text("No chapters to read.")
            self._notify("No chapters to read.")
            Clock.schedule_once(
                lambda dt: MDApp.get_running_app().back(), 0.3)
            return
        start = max(0, min(start, len(self.chapters) - 1))
        self._load_chapter(start)

    # ---------- loading ----------

    def _load_chapter(self, idx):
        if not (0 <= idx < len(self.chapters)) or self._busy:
            return
        self.current = idx
        self._original_text = ""
        self._translated_text = ""
        self._lang = None
        self._offline_lang = None
        self._offline_en_path = ""
        self._offline_tr_path = ""
        self.translate_btn.icon = "translate"
        self._set_busy(True)
        self.title_label.text = self.chapters[idx]["title"]
        self.counter.text = f"{idx + 1}/{len(self.chapters)}"

        ch = self.chapters[idx]
        safe = ch["title"].replace("/", "-").replace(" ", "_")
        en_name = safe + ".txt"
        en_path = os.path.join("novels", self.slug, en_name) \
            if self.slug else None

        # Determine meta.json translation language.
        meta_lang = utils._meta_lang(self.slug) if self.slug else None
        tr_path = utils._translated_path(ch["title"], self.slug, meta_lang) \
            if meta_lang and self.slug else ""

        self._offline_en_path = en_path if en_path and os.path.exists(en_path) else ""
        self._offline_tr_path = tr_path if tr_path and os.path.exists(tr_path) else ""

        # Priority: translated → English → network
        if self._offline_tr_path:
            try:
                with open(self._offline_tr_path, encoding="utf-8") as f:
                    content = f.read()
                self._set_busy(False)
                self._offline_lang = meta_lang
                self._translated_text = content
                self._lang = meta_lang
                self.translate_btn.icon = "undo-variant"
                self._show_text(content, lang=meta_lang)
                progress.mark_seen(self.slug, idx)
            except Exception:
                self._set_busy(False)
                self._notify("Could not read chapter.")
            return

        if self._offline_en_path:
            try:
                with open(self._offline_en_path, encoding="utf-8") as f:
                    content = f.read()
                self._set_busy(False)
                self._original_text = content
                self._show_text(content)
                progress.mark_seen(self.slug, idx)
            except Exception:
                self._set_busy(False)
                self._notify("Could not read chapter.")
            return

        if self.source is None or not ch.get("url"):
            self._set_busy(False)
            self._notify("No source for this chapter.")
            return

        async def coro():
            return await self.source.read_chapter(ch["url"])

        async_loop.run(coro(), self._on_chapter_loaded, timeout=30)

    def _on_chapter_loaded(self, lines, error):
        self._set_busy(False)
        if error is not None or not lines:
            self._show_text(
                "Could not load chapter.\n\n"
                "Check your connection and reopen.")
            self._notify(
                "Failed to load chapter. Check your connection.")
            return
        self._original_text = "\n\n".join(lines)
        self._show_text(self._original_text)
        progress.mark_seen(self.slug, self.current)

    def _show_text(self, text, lang=None):
        self._raw_text = text
        self._shown_lang = lang
        self._disp_key = None  # force rebuild
        self.scroll.scroll_y = 1
        self._render_soon()

    # ---------- chunked rendering ----------
    #
    # One Label == one GL texture, and GPUs cap texture size (4096px on
    # many phones).  A whole chapter in one label exceeds the cap and
    # renders black -- especially right after a font-size change.  The
    # chapter is therefore wrapped into display lines and packed into
    # stacked chunk labels whose textures stay well under the cap.

    def _avail_px(self):
        box = self.body_box
        try:
            return box.width - (box.padding[0] + box.padding[-1])
        except (TypeError, IndexError):
            return box.width

    def _measurer(self, font_name):
        key = (font_name, int(self._font_size))
        meas = self._meas_cache.get(key)
        if meas is None:
            meas = CoreLabel(
                font_name=font_name, font_size=int(self._font_size))
            self._meas_cache[key] = meas
        return meas

    def _line_spacing(self):
        """Pixel distance between two consecutive rendered lines."""
        ar = self._shown_lang == "ar"
        meas = self._measurer(_ARABIC_FONT if ar else "Roboto")
        one = meas.get_extents("Ag")[1]
        two = meas.get_extents("Ag\nAg")[1]
        spacing = (two - one) if two > one else 0
        if spacing <= 0:
            spacing = max(1.0, one * 1.3)
        return spacing

    def _display_lines(self):
        """Final display lines for the current raw text/language/width."""
        text = _strip_control_chars(self._raw_text)
        if self._shown_lang != "ar":
            return self._wrap_plain(text)
        return self._arabic_lines(text)

    def _wrap_plain(self, text):
        avail = self._avail_px()
        if avail <= 0 or not text:
            return text.split("\n")
        meas = self._measurer("Roboto")
        return _wrap_rtl_lines(
            text,
            lambda word: meas.get_extents(word)[0],
            meas.get_extents(" ")[0],
            avail)

    def _arabic_lines(self, text):
        """Wrap FIRST at the real pixel width, then bidi-flip per line.
        Applying get_display() before wrapping makes Kivy wrap the
        reversed string LTR, which scrambles line order and breaks
        words across lines."""
        if not _HAS_ARABIC_SHAPING:
            return text.split("\n")
        reshaped = arabic_reshaper.reshape(text)
        avail = self._avail_px()
        if avail <= 0:
            # Width not laid out yet; flip whole paragraphs.
            # _reflow() re-wraps once the real width is known.
            return [get_display(p, base_dir="R") if p else p
                    for p in reshaped.split("\n")]
        meas = self._measurer(_ARABIC_FONT)
        space_w = meas.get_extents(" ")[0]
        cache = {}

        def measure(word):
            w = cache.get(word)
            if w is None:
                w = meas.get_extents(word)[0]
                cache[word] = w
            return w

        lines = _wrap_rtl_lines(reshaped, measure, space_w, avail)
        return [get_display(l, base_dir="R") if l else l for l in lines]

    def _make_chunk_label(self, text):
        ar = self._shown_lang == "ar"
        lbl = MDLabel(
            text=text,
            font_name=_ARABIC_FONT if ar else "Roboto",
            font_size=self._font_size,
            halign="right" if ar else "left",
        )
        lbl.size_hint_y = None
        lbl.text_size = (self._avail_px(), None)
        lbl.bind(texture_size=lambda inst, sz: setattr(inst, "height", sz[1]))
        return lbl

    def _render_chunks(self):
        lines = self._display_lines()
        per = lines_per_chunk(self._line_spacing())
        chunks = pack_lines_into_chunks(lines, per) or [""]
        box = self.body_box
        box.clear_widgets()
        for chunk in chunks:
            box.add_widget(self._make_chunk_label(chunk))

    def _fallback_render(self):
        """Shaping/layout must never leave the page blank."""
        box = self.body_box
        box.clear_widgets()
        box.add_widget(self._make_chunk_label(
            _strip_control_chars(self._raw_text)))
        self._disp_key = None

    def _reflow(self, *_args):
        w = self.body_box.width
        if w <= 0:
            return
        key = (self._raw_text, self._shown_lang, w, self._font_size)
        if key == self._disp_key:
            return  # already rendered for this exact state
        try:
            self._render_chunks()
        except Exception:
            self._fallback_render()
            return
        self._disp_key = key

    def _render_soon(self):
        if self._font_event is not None:
            self._font_event.cancel()
        self._font_event = Clock.schedule_once(self._reflow, 0)

    # ---------- navigation ----------

    def _next(self):
        if self.current < len(self.chapters) - 1:
            self._load_chapter(self.current + 1)

    def _prev(self):
        if self.current > 0:
            self._load_chapter(self.current - 1)

    def _set_busy(self, busy):
        self._busy = busy
        self.prev_btn.disabled = busy or self.current == 0
        self.next_btn.disabled = busy or self.current == len(self.chapters) - 1

    # ---------- translation ----------

    def _pick_language(self):
        if self._busy or not self._original_text:
            return
        rows = MDList()
        for label, code in LANGUAGES.items():
            rows.add_widget(OneLineListItem(
                text=label, on_release=lambda *_, c=code: self._start_translate(c)))
        self._lang_dialog = MDDialog(title="Translate to", type="custom", content_cls=rows)
        self._lang_dialog.open()

    def _start_translate(self, code):
        if self._lang_dialog is not None:
            self._lang_dialog.dismiss()
        if self._busy or not self._original_text:
            return
        self._set_busy(True)
        self._notify("Translating…")

        async def coro():
            return await asyncio.to_thread(_translate_text, self._original_text, code)

        async_loop.run(
            coro(), lambda res, err, c=code: self._on_translated(res, err, c),
            timeout=180)

    def _on_translated(self, translated, error, code):
        self._set_busy(False)
        if error is not None or not translated:
            self._notify("Translation failed. Check your internet.")
            return
        self._translated_text = translated
        self._lang = code
        self.translate_btn.icon = "undo-variant"
        self._show_text(translated, lang=code)

    def _revert(self):
        if not self._translated_text:
            return
        self._translated_text = ""
        self._lang = None
        self.translate_btn.icon = "translate"
        # If we have an offline English copy, show it; otherwise show
        # whatever was in _original_text (network fetch).
        if self._offline_en_path:
            try:
                with open(self._offline_en_path, encoding="utf-8") as f:
                    content = f.read()
                self._show_text(content)
                return
            except Exception:
                pass
        self._show_text(self._original_text)

    # ---------- font size ----------

    def _font(self, delta):
        self._font_size = min(28, max(14, self._font_size + delta))
        self.font_size_label.text = str(self._font_size)
        from screens.app_settings import save_settings
        save_settings(reader_font_size=self._font_size)
        # Debounce: rapid taps rebuild the chunks only once.
        if self._font_event is not None:
            self._font_event.cancel()
        self._font_event = Clock.schedule_once(self._reflow, 0.15)

    # ---------- misc ----------

    def _back(self):
        progress.flush()   # persist read marks before leaving
        MDApp.get_running_app().back()

    def _notify(self, text):
        MDSnackbar(MDLabel(text=text)).open()
