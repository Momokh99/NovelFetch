# pyright: reportGeneralTypeIssues=true
import asyncio
import json
import os
import time
from datetime import datetime, timedelta

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.relativelayout import RelativeLayout
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.fitimage import FitImage
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen

from core.downloader import download as _download_novel
from core.library import (
    display_title as _display_title,
    library_entries as _library_entries,
    local_chapter_count as _local_chapter_count,
    local_chapters as _local_chapters,
    meta_lang as _meta_lang,
    missing_chapters as _missing_chapters,
    read_meta as _read_meta,
    save_cover as _save_cover,
    update_chapters_meta as _update_chapters_meta,
)
from core.utils import _get_chapters, _get_source
from gui.async_runner import async_loop
from gui.screens import theme
from gui.screens.app_settings import load_settings
from gui.screens.utils import _open_chapters_for, _snack, _time_ago

_PERSIST_FILE = "update_results.json"


def _gap_spacer():
    return MDBoxLayout(size_hint_y=None, height=theme.SECTION_GAP)


def _reconcile(results):
    out = []
    for r in results:
        slug = r.get("slug", "")
        total = r.get("total") or len(r.get("chapters", []))
        local = _local_chapter_count(slug)
        new = max(0, total - local)
        if new == 0:
            continue
        r["new"] = new
        lang = r.get("lang", "")
        r["chapters"] = _missing_chapters(r.get("chapters", []), slug, lang)
        r["title"] = _display_title(slug, r.get("title", ""))
        out.append(r)
    return out


def _load_persisted():
    try:
        with open(_PERSIST_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    for r in data.get("results", []):
        r.setdefault("chapters", [])
    return _reconcile(data.get("results", []))


def _save_persisted(results):
    payload = {
        "saved_at": int(time.time()),
        "results": [{k: v for k, v in r.items() if k != "source"} for r in results],
    }
    try:
        with open(_PERSIST_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except OSError:
        pass


class UpdateTab(MDScreen):
    """Checks each library novel against its source's chapter list and lists
    the ones that have new chapters online, with a per-row update download."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._busy = False
        self._batch_busy = False
        self._auto_armed = False
        self._results = []

        # Widget tree lives in kv/update.kv; alias the runtime-touched nodes.
        self.topbar = self.ids.topbar
        self.topbar.set_actions([
            ("refresh", self.refresh),
            ("image-refresh", self.update_covers),
            ("download-multiple", self.update_all),
        ])
        self.info_label = self.ids.info_label
        self.empty_box = self.ids.empty_box
        self.empty_label = self.ids.empty_label
        self.empty_sub = self.ids.empty_sub
        self.list_view = self.ids.list_view

        self._results = _load_persisted()
        if self._results:
            _save_persisted(self._results)
            self._render(self._results)
        else:
            self.info_label.text = ""
            self.empty_label.text = "No updates yet"
            self.empty_sub.text = "Tap refresh to check for updates."
            self.empty_box.opacity = 1
            self.empty_box.height = self.empty_box.minimum_height

    def load(self, **kwargs):
        self.refresh()

    def update_covers(self):
        """Re-download the cover for every library novel (also fetching any
        missing ones), updating meta.json. Runs in the background so the UI
        stays responsive; results land in a snackbar."""
        if getattr(self, "_cover_busy", False):
            return
        self._cover_busy = True
        self.info_label.text = "Updating covers…"

        async def coro():
            # Concurrent cover fetches (bounded) instead of one-by-one.
            entries = list(_library_entries())
            sem = asyncio.Semaphore(4)

            async def cover_one(entry):
                async with sem:
                    slug = entry["slug"]
                    source = _get_source(slug)
                    if source is None or getattr(source, "blocked", False):
                        return (0, 1)
                    try:
                        cover = await _save_cover(source, slug)
                    except Exception:
                        return (0, 1)
                    if not cover:
                        return (0, 1)
                    meta = dict(_read_meta(slug))
                    meta.setdefault("title", entry["title"] or slug)
                    meta.setdefault("chapters", entry.get("count") or 0)
                    meta.setdefault("source", source.name)
                    meta["cover"] = cover
                    meta["tracked"] = True
                    try:
                        os.makedirs(os.path.join("novels", slug), exist_ok=True)
                        with open(os.path.join("novels", slug, "meta.json"),
                                  "w") as f:
                            json.dump(meta, f)
                    except OSError:
                        return (0, 1)
                    return (1, 0)

            results = await asyncio.gather(
                *(cover_one(e) for e in entries))
            updated = sum(r[0] for r in results)
            skipped = sum(r[1] for r in results)
            return updated, skipped

        def on_done(result, error):
            self._cover_busy = False
            self.refresh()
            app = MDApp.get_running_app()
            if error is not None:
                _snack("Update covers failed")
                return
            updated, skipped = result
            if hasattr(app.root, "homescreen_library_refresh"):
                app.root.homescreen_library_refresh()
            _snack(f"Updated {updated} cover(s), {skipped} skipped")

        async_loop.run(coro(), on_done, timeout=300)

    def update_all(self):
        """Background batch: download the new chapters for every novel that
        has updates, showing one running indicator instead of per-novel
        screens. Runs sequentially per novel on the async loop."""
        if self._batch_busy:
            return
        results = [r for r in self._results if r.get("chapters")]
        if not results:
            _snack("No updates to download")
            return
        self._batch_busy = True
        self.info_label.text = "Downloading updates…"

        has_translate = any(r.get("lang") for r in results)
        dl_timeout = 3600 if has_translate else 600

        async def coro():
            total_saved = 0
            total_failed = 0
            for i, res in enumerate(results, 1):
                lang = res.get("lang", "")
                saved, failed = await _download_novel(
                    res["source"], res["slug"], res["chapters"], res["title"],
                    total=res["total"],
                    translate=bool(lang), lang=lang)
                total_saved += saved
                total_failed += failed
                i_ = i
                n_ = len(results)
                Clock.schedule_once(
                    lambda dt: self._set_batch_progress(i_, n_), 0)
            return total_saved, total_failed, len(results)

        def on_done(result, error):
            self._batch_busy = False
            self._auto_armed = False
            self.refresh()
            app = MDApp.get_running_app()
            if hasattr(app.root, "homescreen_library_refresh"):
                app.root.homescreen_library_refresh()
            if error is not None:
                _snack("Update download failed")
                return
            saved, failed, total = result
            _snack(f"Updated {total} novel(s): {saved} saved"
                   + (f", {failed} failed" if failed else ""))

        async_loop.run(coro(), on_done, timeout=dl_timeout)

    def _set_batch_progress(self, i, total):
        self.info_label.text = f"Downloading updates… {i}/{total}"

    def refresh(self):
        if self._busy:
            return
        self._busy = True
        self._auto_armed = True
        self.list_view.clear_widgets()
        self.empty_label.text = ""
        self.info_label.text = "Checking for updates…"

        async def coro():
            # Check every novel concurrently (bounded) — the fetch_chapters
            # round-trips no longer add up serially for a large library.
            entries = list(_library_entries())
            sem = asyncio.Semaphore(4)

            async def check_one(n):
                async with sem:
                    slug = n["slug"]
                    source = _get_source(slug)
                    if source is None or getattr(source, "blocked", False):
                        return None
                    raw = slug.split(":", 1)[-1] if ":" in slug else slug
                    try:
                        chapters = await _get_chapters(source, raw)
                    except Exception:
                        return None
                    if not chapters:
                        return None
                    now = int(time.time())
                    online = len(chapters)
                    stored = _read_meta(slug).get("chapters", 0)
                    if online != stored:
                        _update_chapters_meta(slug, online, now)
                    if online <= stored:
                        return None
                    new_chapters = chapters[stored:]
                    return {
                        "slug": slug,
                        "title": _display_title(slug, n["title"]),
                        "new": len(new_chapters),
                        "chapters": new_chapters,
                        "source": source,
                        "total": online,
                        "updated_ts": now,
                        "lang": _meta_lang(slug) or "",
                    }

            results = await asyncio.gather(*(check_one(n) for n in entries))
            return [r for r in results if r]

        async_loop.run(coro(), self._on_done)

    def _on_done(self, results, error):
        self._busy = False
        if error is not None:
            self._render(self._results)
            self.info_label.text = "Update check failed — showing last results"
            return
        self._results = results or []
        _save_persisted(self._results)
        self._render(self._results)
        if self._auto_armed and self._update_and_download() and self._results:
            self._auto_armed = False
            Clock.schedule_once(lambda dt: self.update_all(), 0.2)

    def _update_and_download(self):
        return bool(load_settings().get("update_and_download", False))

    def _render(self, results):
        self.list_view.clear_widgets()
        if not results:
            self.info_label.text = ""
            self.empty_label.text = "All novels are up to date"
            self.empty_sub.text = "Tap refresh to check again."
            self.empty_box.opacity = 1
            self.empty_box.height = self.empty_box.minimum_height
            return
        self.empty_box.opacity = 0
        self.empty_box.height = 0
        max_ts = max((r.get("updated_ts") or 0 for r in results), default=0)
        ago = _time_ago(max_ts)
        self.info_label.text = (
            f"{len(results)} novel(s) with new chapters"
            + (f" · Last updated {ago}" if ago else ""))
        first = True
        for header, group in self._bucket(results):
            if not first:
                self.list_view.add_widget(_gap_spacer())
            first = False
            if header:
                self.list_view.add_widget(self._make_header(header))
            for r in group:
                self.list_view.add_widget(self._make_row(r))

    @staticmethod
    def _bucket(results):
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        week_start = today - timedelta(days=today.weekday())

        def bucket_for(r):
            ts = r.get("updated_ts", 0)
            if not ts:
                return "Older"
            dt = datetime.fromtimestamp(ts).replace(
                hour=0, minute=0, second=0, microsecond=0)
            if dt >= today:
                return "Today"
            if dt >= yesterday:
                return "Yesterday"
            if dt >= week_start:
                return "This week"
            return "Older"

        order = ["Today", "Yesterday", "This week", "Older"]
        buckets = {b: [] for b in order}
        for r in results:
            buckets[bucket_for(r)].append(r)
        return [(b, buckets[b]) for b in order if buckets[b]]

    @staticmethod
    def _make_header(text):
        box = MDBoxLayout(
            orientation="vertical", adaptive_height=True,
            padding=(dp(4), dp(2), dp(4), dp(10)))
        box.add_widget(MDLabel(
            text=text, bold=True,
            theme_text_color="Secondary",
            font_style="Label", role="large"))
        return box

    def _make_row(self, res):
        row = MDCard(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(76),
            padding=theme.CARD_PAD, spacing=theme.CARD_GAP,
        )
        cover = _read_meta(res["slug"]).get("cover", "")
        if cover:
            cover_box = MDBoxLayout(
                size_hint=(None, 1), width=dp(48),
                radius=[8, 8, 8, 8], md_bg_color=theme.surface_color(),
            )
            cover_box.add_widget(FitImage(
                source=os.path.join("novels", res["slug"], cover),
                radius=[8, 8, 8, 8], size_hint=(1, 1)))
            row.add_widget(cover_box)
        texts = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(50), spacing="2dp",
                            pos_hint={"center_x": 0.5, "center_y": 0.5})
        texts.add_widget(MDLabel(
            text=res["title"], bold=True,
            font_style="Title", role="medium", size_hint_y=None, height="28dp",
            shorten=True, shorten_from="right", max_lines=1))
        texts.add_widget(MDLabel(
            text=f"{res['new']} new chapter(s)", theme_text_color="Secondary",
            font_style="Label", role="large", size_hint_y=None, height="20dp"))
        texts_rl = RelativeLayout(size_hint=(1, 1))
        texts_rl.add_widget(texts)
        row.add_widget(texts_rl)
        # Center the action button vertically within the row.
        btn = MDIconButton(icon="download", on_release=lambda *_, r=res: self._update(r),
                           pos_hint={"center_x": 0.5, "center_y": 0.5})
        btn_rl = RelativeLayout(size_hint=(None, 1), width=dp(48))
        btn_rl.add_widget(btn)
        row.add_widget(btn_rl)
        row.on_release = lambda r=res: self._open(r)
        return row

    def _open(self, res):
        source = res.get("source") or _get_source(res["slug"])
        _open_chapters_for(
            {"slug": res["slug"].split(":", 1)[-1], "title": res["title"], "cover": ""},
            source,
            fallback=_local_chapters(res["slug"]),
        )

    def _update(self, res):
        if not res.get("chapters"):
            return
        source = res.get("source") or _get_source(res["slug"])
        lang = res.get("lang", "")
        MDApp.get_running_app().goto(
            "download_progress",
            chapters=res["chapters"],
            slug=res["slug"],
            source=source,
            title=res["title"],
            total=res["total"],
            translate=bool(lang),
            lang=lang,
        )
