import math

from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.scrollview import ScrollView
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDIcon, MDLabel

STYLES = [
    ("Linear Bar", "horizontal fill bar", "linear"),
    ("Percentage Circle", "ring arc with % text", "circle"),
    ("Chapter Badge", "rounded fraction pill", "badge"),
    ("Segmented Blocks", "one block per chapter", "blocks"),
    ("Reading Status", "state pill, no numbers", "pill"),
    ("Progress Ring on Cover", "arc drawn on the cover", "ringcover"),
    ("Minimal Text", "just the chapter text", "text"),
    ("Gradient Bar", "fill fades color", "gradient"),
    ("Vertical Side Bar", "thin bar on the card edge", "sidebar"),
    ("Wave Fill on Cover", "wave overlay on the cover", "wave"),
    ("Segmented Dots", "one dot per chapter", "dots"),
    ("Dual Bar", "read + downloaded", "dual"),
]


def _track():
    return (0.55, 0.55, 0.6, 0.18)


def _arc_points(cx, cy, r, start_deg, sweep_deg, steps=48):
    pts = []
    for i in range(steps + 1):
        ang = math.radians(start_deg + sweep_deg * i / steps)
        pts += [cx + r * math.cos(ang), cy + r * math.sin(ang)]
    return pts


class Indicator(MDBoxLayout):
    style = StringProperty("linear")
    frac = NumericProperty(0.42)
    state = StringProperty("Reading")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._label = MDLabel(
            halign="center", valign="middle", font_style="Caption",
            bold=True, font_size=sp(11), theme_text_color="Primary")
        self.add_widget(self._label)
        self.bind(size=self._redraw, style=self._redraw,
                  frac=self._redraw, state=self._redraw)
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        if self.style == "text":
            return
        app = MDApp.get_running_app()
        if app is None:
            return
        prim = list(app.theme_cls.primary_color)
        w, h = self.width, self.height
        if w <= 0 or h <= 0:
            return
        frac = max(0.0, min(1.0, self.frac))
        with self.canvas:
            if self.style == "linear":
                from kivy.graphics import Color, RoundedRectangle
                Color(*_track())
                RoundedRectangle(pos=self.pos, size=(w, h), radius=[h / 2] * 4)
                Color(*prim)
                RoundedRectangle(pos=self.pos, size=(w * frac, h),
                                 radius=[h / 2, h / 2, h / 2, h / 2])
            elif self.style == "gradient":
                from kivy.graphics import Color, RoundedRectangle
                Color(*_track())
                RoundedRectangle(pos=self.pos, size=(w, h), radius=[h / 2] * 4)
                n = 24
                x0, y0 = self.x, self.y
                rw = w * frac / n
                for i in range(n):
                    t = i / max(n - 1, 1)
                    col = [p + (1 - p) * 0.55 * t for p in prim[:3]]
                    Color(col[0], col[1], col[2], prim[3])
                    RoundedRectangle(pos=(x0 + i * rw, y0), size=(rw, h),
                                     radius=[0, 0, 0, 0])
            elif self.style == "circle":
                from kivy.graphics import Color, Line
                cx, cy = self.center_x, self.center_y
                r = min(w, h) / 2 - dp(4)
                lw = dp(5)
                Color(*_track())
                Line(circle=(cx, cy, r), width=lw)
                Color(*prim)
                Line(points=_arc_points(cx, cy, r, 90, -360 * frac), width=lw)
                self._label.text = f"{int(round(frac * 100))}%"
            elif self.style == "badge":
                from kivy.graphics import Color, RoundedRectangle
                Color(prim[0], prim[1], prim[2], 0.18)
                RoundedRectangle(pos=self.pos, size=(w, h), radius=[h / 2] * 4)
                Color(*prim)
                RoundedRectangle(pos=self.pos, size=(w * frac, h),
                                 radius=[h / 2, h / 2, h / 2, h / 2])
                self._label.text = self.state
            elif self.style in ("blocks", "dots"):
                from kivy.graphics import Color, Ellipse, RoundedRectangle
                n = 12
                gap = dp(2)
                cw = (w - gap * (n - 1)) / n
                filled = int(round(frac * n))
                for i in range(n):
                    x = self.x + i * (cw + gap)
                    if self.style == "dots":
                        d = cw - dp(2)
                        pos = (x + (cw - d) / 2, self.y + (h - d) / 2)
                        if i < filled:
                            Color(*prim)
                            Ellipse(pos=pos, size=(d, d))
                        else:
                            Color(*_track())
                            Ellipse(pos=pos, size=(d, d))
                    else:
                        if i < filled:
                            Color(*prim)
                            RoundedRectangle(pos=(x, self.y), size=(cw, h),
                                             radius=[dp(2)] * 4)
                        else:
                            Color(*_track())
                            RoundedRectangle(pos=(x, self.y), size=(cw, h),
                                             radius=[dp(2)] * 4)
                self._label.text = ""
            elif self.style == "pill":
                from kivy.graphics import Color, RoundedRectangle
                color = prim if self.state == "Reading" else (0.4, 0.7, 0.4, 1)
                if self.state == "Finished":
                    color = (0.3, 0.6, 0.9, 1)
                Color(color[0], color[1], color[2], 0.2)
                RoundedRectangle(pos=self.pos, size=(w, h), radius=[h / 2] * 4)
                Color(color[0], color[1], color[2], 1)
                self._label.theme_text_color = "Custom"
                self._label.text_color = \
                    (color[0], color[1], color[2], 1)
                self._label.text = f"Reading"
            elif self.style == "ringcover":
                from kivy.graphics import Color, Line
                cx, cy = self.center_x, self.center_y
                r = min(w, h) / 2 - dp(4)
                lw = dp(4)
                Color(*_track())
                Line(circle=(cx, cy, r), width=lw)
                Color(*prim)
                Line(points=_arc_points(cx, cy, r, 90, -360 * frac), width=lw)
                self._label.text = ""
            elif self.style == "sidebar":
                from kivy.graphics import Color, RoundedRectangle
                Color(*_track())
                RoundedRectangle(pos=self.pos, size=(w, h),
                                 radius=[dp(2)] * 4)
                Color(*prim)
                RoundedRectangle(pos=(self.x, self.y),
                                 size=(w, h * frac),
                                 radius=[dp(2), dp(2), 0, 0])
                self._label.text = ""
            elif self.style == "wave":
                from kivy.graphics import Color, RoundedRectangle
                amp = dp(2.5)
                base = h * (1 - frac)
                col_w = 4.0
                x = self.x
                while x < self.x + w:
                    t = (x - self.x) / w
                    top = base + amp * math.sin(t * 4 * math.pi)
                    Color(prim[0], prim[1], prim[2], 0.35)
                    RoundedRectangle(pos=(x, self.y + top),
                                     size=(col_w, h - top),
                                     radius=[0, 0, 0, 0])
                    x += col_w
                self._label.text = ""
            elif self.style == "dual":
                from kivy.graphics import Color, RoundedRectangle
                bh = (h - dp(3)) / 2
                Color(*_track())
                RoundedRectangle(pos=(self.x, self.y), size=(w, bh),
                                 radius=[dp(2)] * 4)
                RoundedRectangle(pos=(self.x, self.y + bh + dp(3)),
                                 size=(w, bh), radius=[dp(2)] * 4)
                Color(*prim)
                RoundedRectangle(pos=(self.x, self.y), size=(w * frac, bh),
                                 radius=[dp(2)] * 4)
                Color(0.2, 0.7, 0.6, 1)
                RoundedRectangle(pos=(self.x, self.y + bh + dp(3)),
                                 size=(w * 0.8, bh), radius=[dp(2)] * 4)
                self._label.text = ""


class CoverPlaceholder(MDBoxLayout):
    pass


class PreviewApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.theme_style = "Dark"

        root = MDBoxLayout(orientation="vertical")
        root.add_widget(MDLabel(
            text="Read indication styles — pick your favorite",
            bold=True, size_hint_y=None, height=dp(48),
            padding=(dp(16), 0, 0, 0), valign="middle"))
        scroll = ScrollView(bar_width=dp(6))
        content = MDBoxLayout(
            orientation="vertical", adaptive_height=True,
            padding=dp(12), spacing=dp(14))
        for i, (name, note, style) in enumerate(STYLES):
            content.add_widget(self._style_block(i + 1, name, note, style))
        scroll.add_widget(content)
        root.add_widget(scroll)
        return root

    def _style_block(self, num, name, note, style):
        block = MDBoxLayout(
            orientation="vertical", adaptive_height=True, spacing=dp(4))
        block.add_widget(MDLabel(
            text=f"{num}. {name} — {note}",
            theme_text_color="Secondary", font_style="Caption",
            size_hint_y=None, height=dp(18)))
        block.add_widget(self._row(style))
        return block

    def _row(self, style):
        row = MDCard(
            orientation="horizontal", size_hint_y=None, height=dp(124),
            padding=dp(12), spacing=dp(16), elevation=2, radius=[dp(12)] * 4)
        cover = CoverPlaceholder(
            size_hint=(None, 1), width=dp(62), radius=[dp(8)] * 4,
            md_bg_color=(0.24, 0.25, 0.32, 1))
        cover.add_widget(MDIcon(
            icon="book-open-variant", halign="center", valign="middle",
            font_size=sp(26), theme_text_color="Secondary"))
        if style in ("ringcover", "wave"):
            overlay = Indicator(
                style=style, frac=0.42, state="Reading",
                size_hint=(1, 1), radius=[dp(8)] * 4, md_bg_color=(0, 0, 0, 0))
            cover.add_widget(overlay)
        row.add_widget(cover)

        texts = MDBoxLayout(orientation="vertical", size_hint_y=1, spacing=dp(2))
        texts.add_widget(MDLabel(
            text="Shadow Lord", bold=True, font_style="Subtitle1",
            size_hint_y=None, height=dp(30), shorten=True,
            shorten_from="right", max_lines=1))
        texts.add_widget(MDLabel(
            text="Ch. 42 of 100 · RoyalRoad",
            theme_text_color="Secondary", font_style="Caption",
            size_hint_y=None, height=dp(18)))

        if style == "text":
            texts.add_widget(MDLabel(
                text="Ch. 42 of 100", theme_text_color="Primary",
                font_style="Caption", bold=True,
                size_hint_y=None, height=dp(18)))
        elif style in ("linear", "gradient", "blocks", "dots",
                       "circle", "badge", "pill", "dual"):
            ind = Indicator(
                style=style, frac=0.42, state="Reading",
                size_hint_y=None, height=dp(20))
            texts.add_widget(ind)

        row.add_widget(texts)

        if style == "sidebar":
            bar = Indicator(
                style="sidebar", frac=0.42, state="Reading",
                size_hint=(None, 1), width=dp(4))
            row.add_widget(bar)
        return row


if __name__ == "__main__":
    PreviewApp().run()