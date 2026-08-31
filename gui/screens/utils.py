# pyright: reportGeneralTypeIssues=true
import asyncio
import json
import os
import re
import shutil
import time

from kivymd.app import MDApp
from kivymd.uix.button import MDIconButton
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText

from core.progress import LANGUAGES, PROGRESS_FILE
from core.utils import _get_chapters, _get_source
from gui.async_runner import async_loop

_LANG_CODES = set(LANGUAGES.values())
_TRANSL_SUFFIX_RE = re.compile(r"^(.+)_([a-z]{2}(?:-[a-z]{2})?)\.txt$")
_DIGIT_PREFIX_RE = re.compile(r"^\d+/")


def _is_translation_file(fname):
    """Return the lang code if *fname* is a translation file, else None."""
    m = _TRANSL_SUFFIX_RE.match(fname)
    if m and m.group(2) in _LANG_CODES:
        return m.group(2)
    return None


def _snack(text):
    MDSnackbar(MDSnackbarText(text=text)).open()

def _time_ago(timestamp):
    """'just now / 5m ago / 3h ago / 2d ago / 4w ago' from a unix timestamp."""
    if not timestamp:
        return ""
    delta = time.time() - timestamp
    if delta < 60:
        return "just now"
    minutes = int(delta // 60)
    if minutes < 60:
        return f"{minutes}m ago"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours}h ago"
    days = int(hours // 24)
    if days < 7:
        return f"{days}d ago"
    weeks = int(days // 7)
    return f"{weeks}w ago"


def _read_last_updated(slug):
    """Unix timestamp of the last update check that found new chapters, or 0."""
    try:
        return int(_read_meta(slug).get("last_updated") or 0)
    except (OSError, ValueError):
        return 0


def _write_last_updated(slug, ts):
    """Persist the last-updated timestamp into the novel's meta.json."""
    try:
        meta = dict(_read_meta(slug))
        meta["last_updated"] = int(ts)
        os.makedirs(os.path.join("novels", slug), exist_ok=True)
        with open(os.path.join("novels", slug, "meta.json"), "w") as f:
            json.dump(meta, f)
    except OSError:
        pass


def _update_chapters_meta(slug, count, ts):
    """Update meta.json with the source's total chapter count and a timestamp."""
    try:
        meta = dict(_read_meta(slug))
        meta["chapters"] = int(count)
        meta["last_updated"] = int(ts)
        os.makedirs(os.path.join("novels", slug), exist_ok=True)
        with open(os.path.join("novels", slug, "meta.json"), "w") as f:
            json.dump(meta, f)
    except OSError:
        pass


def _chapter_sort_key(fname):
    nums = re.findall(r"\d+", fname)
    return int(nums[0]) if nums else 0


def _local_chapters(slug):
    """Build a chapter list from the downloaded novels/{slug}/*.txt files.

    Translation-suffixed files ({title}_{lang}.txt) are excluded so chapter
    counts and indices stay canonical."""
    chap_dir = os.path.join("novels", slug)
    if not os.path.isdir(chap_dir):
        return []
    files = [f for f in os.listdir(chap_dir)
             if f.endswith(".txt") and _is_translation_file(f) is None]
    files.sort(key=_chapter_sort_key)
    chapters = []
    for i, f in enumerate(files, 1):
        title = os.path.basename(f).replace(".txt", "").replace("_", " ").title()
        chapters.append({"num": i, "title": title, "url": ""})
    return chapters


def _local_chapter_count(slug):
    """Distinct downloaded chapters for a novel, counting the novel's own
    translation-language files as real chapters (so an update check does not
    re-report them as new). Canonical and translated copies of the same
    chapter count once."""
    chap_dir = os.path.join("novels", slug)
    if not os.path.isdir(chap_dir):
        return 0
    lang = _meta_lang(slug)
    bases = set()
    try:
        for f in os.listdir(chap_dir):
            if not f.endswith(".txt"):
                continue
            tl = _is_translation_file(f)
            if tl is None:
                bases.add(f)
            elif tl == lang:
                bases.add(f[: -len("_%s.txt" % lang)] + ".txt")
    except OSError:
        return 0
    return len(bases)


def _delete_library(slug, untrack=False):
    """Remove a novel's files and its reading progress. Tracking survives by
    default so the novel stays in the library (tracked-only) and can be
    re-downloaded; pass untrack=True for a full removal."""
    from core.progress import progress
    shutil.rmtree(os.path.join("novels", slug), ignore_errors=True)
    progress.remove(slug)
    if untrack:
        progress.untrack(slug)
    progress.flush()


def _read_meta(slug):
    """Per-novel meta.json: {"title": ..., "cover": "cover.jpg"} or {}."""
    try:
        with open(os.path.join("novels", slug, "meta.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _meta_lang(slug):
    """Return the saved translation language code for a novel, or None."""
    return _read_meta(slug).get("lang")


def _translated_path(chapter_title, slug, lang):
    """Return the local path for a translated chapter file, or ''."""
    if not lang:
        return ""
    safe = chapter_title.replace("/", "-").replace(" ", "_")
    return os.path.join("novels", slug, f"{safe}_{lang}.txt")


def _has_chapters(slug):
    """True if any downloaded chapter .txt exists under novels/{slug}."""
    path = os.path.join("novels", slug)
    if not os.path.isdir(path):
        return False
    return any(name.endswith(".txt") and _is_translation_file(name) is None
               for name in os.listdir(path))


def _missing_chapters(chapters, slug, lang):
    """Return chapters whose local file is not present under novels/{slug}."""
    lang = lang or ""
    chap_dir = os.path.join("novels", slug)
    if not os.path.isdir(chap_dir):
        return list(chapters)
    missing = []
    for ch in chapters:
        safe = ch["title"].replace("/", "-").replace(" ", "_")
        if lang:
            path = os.path.join(chap_dir, f"{safe}_{lang}.txt")
        else:
            path = os.path.join(chap_dir, f"{safe}.txt")
        if not os.path.exists(path):
            missing.append(ch)
    return missing


def _display_title(slug, fallback):
    """Clean novel title for UI display: prefer meta title, then strip
    the numeric id-prefix from slug-derived fallbacks (e.g. '136609/Ashland'
    → 'Ashland')."""
    meta_title = _read_meta(slug).get("title")
    if meta_title and not _DIGIT_PREFIX_RE.match(meta_title):
        return meta_title
    raw = slug.split(":", 1)[-1] if ":" in slug else slug
    if _DIGIT_PREFIX_RE.match(raw):
        raw = raw.split("/", 1)[1]
    return raw.replace("-", " ").title()


def _is_tracked(slug):
    """True if a slug is registered as tracked, via meta.json or the
    tracking registry (which persists even after the folder is deleted)."""
    from core.progress import progress
    return bool(_read_meta(slug).get("tracked")) or progress.is_tracked(slug)


def _library_entries():
    """Every library novel: folders on disk plus tracked-but-deleted slugs.

    Each entry: {slug, title, count, tracked} — tracked slugs whose files are
    gone still show up so the reader can re-add/update them."""
    from core.progress import _scan_library, progress
    entries = _scan_library()
    seen = {n["slug"] for n in entries}
    for t in progress.tracked_novels():
        if t["slug"] not in seen:
            entries.append({"slug": t["slug"], "title": t["title"], "count": 0})
    entries.sort(key=lambda n: n["slug"])
    return entries


def _library_sig_rows(entries):
    """Per-folder (slug, count, dir_mtime, top_mtime) rows used by
    _library_fingerprint(), built from an already-scanned entries list
    instead of walking novels/ again."""
    novels_dir = "novels"
    sig = []
    for n in entries:
        slug = n["slug"]
        folder = os.path.join(novels_dir, slug)
        try:
            files = os.listdir(folder)
        except OSError:
            continue
        # Directory mtime bumps when chapter files appear/disappear; meta.json
        # and cover.* mtimes catch in-place rewrites (title/cover updates).
        top = 0.0
        for f in files:
            if f != "meta.json" and not f.startswith("cover."):
                continue
            try:
                top = max(top, round(os.path.getmtime(
                    os.path.join(folder, f)), 6))
            except OSError:
                pass
        try:
            dir_mtime = round(os.stat(folder).st_mtime, 6)
        except OSError:
            dir_mtime = 0.0
        sig.append((slug, n["count"], dir_mtime, top))
    sig.sort()
    return sig


def _library_entries_and_fingerprint():
    """Single-pass version of _library_entries() + _library_fingerprint():
    scans the novels/ tree once and derives both from it, instead of two
    independent full-tree walks back to back."""
    entries = _library_entries()
    sig = _library_sig_rows(entries)
    try:
        prog_mtime = round(os.path.getmtime(PROGRESS_FILE), 6)
    except OSError:
        prog_mtime = -1.0
    return entries, repr((sig, prog_mtime))


def _library_fingerprint():
    """Cheap signature of everything the library views depend on: the
    novels/ tree (per-folder chapter counts + dir and meta/cover mtimes)
    and progress.json (tracked/read state).

    Equal fingerprints ⇒ the on-screen library is up to date, so callers can
    skip rebuilding widget trees. Reuses _scan_library()'s (recursive) walk
    so novels whose slug contains a '/' — e.g. royalroad's "id/title" slugs,
    which nest two directories deep — are covered too."""
    _, fp = _library_entries_and_fingerprint()
    return fp


async def _track_novel(source, novel):
    """Register a novel in the library without downloading chapters.

    Writes novels/{qualified}/meta.json with title, cover, source, and the
    tracked flag. chapters starts at 0 and is only written later by a real
    download, so 'Add' stays instant even for slow sources. Returns the
    qualified slug."""
    qualified = source.qualify_slug(novel["slug"])
    cover = await _save_cover(source, qualified)
    meta = {
        "title": novel.get("title") or novel["slug"],
        "cover": cover,
        "chapters": 0,
        "source": source.name,
        "tracked": True,
    }
    try:
        os.makedirs(os.path.join("novels", qualified), exist_ok=True)
        with open(os.path.join("novels", qualified, "meta.json"), "w") as f:
            json.dump(meta, f)
    except OSError:
        raise
    # Tracking is also persisted in novels/tracking.json so it survives even
    # if the novels/{qualified} folder is later deleted.
    from core.progress import progress
    progress.track(qualified, meta["title"])
    progress.flush()
    return qualified


def _add_to_library_icon(novel, source):
    """Bookmark-style quick-add button for a result row. Uses a bookmark icon
    when the novel is already registered in the library."""
    qualified = ""
    if source is not None:
        qualified = source.qualify_slug(novel["slug"])
    registered = bool(qualified and _read_meta(qualified))

    btn = MDIconButton(
        icon="bookmark" if registered else "bookmark-plus-outline",
        size_hint=(None, 1),
        on_release=lambda *_: _add_flow(btn, novel, source),
    )
    if registered:
        btn.disabled = True
    return btn


def _add_flow(btn, novel, source):
    """Add-to-library tap handler. Disables the button while the async save
    runs, then swaps the icon and refreshes the Home library list."""
    if source is None:
        _snack("No source for this novel.")
        return
    qualified = source.qualify_slug(novel["slug"])
    if _read_meta(qualified):
        _snack("Already in your library.")
        return

    async def coro():
        return await _track_novel(source, novel)

    def on_done(result, error):
        btn.disabled = False
        if error is not None:
            _snack("Could not add. Check your connection.")
            return
        btn.icon = "bookmark"
        _snack("Added to library.")
        app = MDApp.get_running_app()
        root = app.root if app is not None else None
        if root is not None and hasattr(root, "homescreen_library_refresh"):
            root.homescreen_library_refresh()

    btn.disabled = True
    async_loop.run(coro(), on_done, timeout=30)


async def _save_cover(source, qualified_slug):
    """Download the novel cover into novels/{qualified_slug}/, return filename."""
    raw = qualified_slug.split(":", 1)[-1] if ":" in qualified_slug else qualified_slug
    try:
        url = await source.cover_url(raw)
        if not url:
            return ""
        client = _get_http_client()
        resp = await client.get(url)
        if resp.status_code != 200:
            return ""
        ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
        if ext not in ("jpg", "jpeg", "png", "webp"):
            ext = "jpg"
        name = f"cover.{ext}"
        os.makedirs(os.path.join("novels", qualified_slug), exist_ok=True)
        with open(os.path.join("novels", qualified_slug, name), "wb") as f:
            f.write(resp.content)
        return name
    except Exception:
        return ""


_COVER_CACHE_DIR = os.path.join("novels", ".covers")
_shared_http_client = None

# In-flight cover downloads, keyed by URL: concurrent callers for the same
# URL share one request instead of each firing its own.  Created lazily by
# _download_cover, so it stays safe across async_loop restarts.
_COVER_INFLIGHT: dict[str, "asyncio.Future[str]"] = {}
_COVER_LOCK = asyncio.Lock()


def _get_http_client():
    """Shared httpx.AsyncClient with a 30s timeout (created once)."""
    global _shared_http_client
    if _shared_http_client is None:
        import httpx
        _shared_http_client = httpx.AsyncClient(follow_redirects=True, timeout=30)
    return _shared_http_client


def _cover_cache_path(url):
    """Deterministic local path for a remote cover URL (no network here)."""
    if not url:
        return ""
    import hashlib
    digest = hashlib.md5(url.encode("utf-8")).hexdigest()
    ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"
    return os.path.join(_COVER_CACHE_DIR, f"{digest}.{ext}")


def _cached_cover(url):
    """Local path if the cover is already cached, else ''."""
    path = _cover_cache_path(url)
    if path and os.path.exists(path):
        return path
    return ""


async def _download_cover(url):
    """httpx-download a remote cover into the shared cache dir (once).

    Concurrent callers for the same URL share a single in-flight download:
    the first registers a future and fetches, the rest await that future
    instead of issuing duplicate requests."""
    path = _cover_cache_path(url)
    if not path or os.path.exists(path):
        return path
    waiter = None
    async with _COVER_LOCK:
        if os.path.exists(path):
            # A prior waiter finished while we waited on the lock.
            return path
        fut = _COVER_INFLIGHT.get(url)
        if fut is not None:
            waiter = fut
        else:
            fut = asyncio.get_running_loop().create_future()
            _COVER_INFLIGHT[url] = fut
    if waiter is not None:
        try:
            return await asyncio.shield(waiter)
        except Exception:
            return ""
    # Only the registered owner downloads; the lock is released so waiters
    # block on the future below instead of on the lock.
    result = path
    try:
        os.makedirs(_COVER_CACHE_DIR, exist_ok=True)
        client = _get_http_client()
        resp = await client.get(url)
        if resp.status_code != 200:
            result = ""
        else:
            tmp = path + ".tmp"
            with open(tmp, "wb") as f:
                f.write(resp.content)
            os.replace(tmp, path)
    except Exception:
        result = ""
    _COVER_INFLIGHT.pop(url, None)
    if not fut.done():
        fut.set_result(result)
    return result


def set_image_url(img, url):
    """Point an AsyncImage at a cover URL, downloading to a local cache first.

    Remote AsyncImage sources fail on Android (Kivy hardcodes a cafile path that
    does not exist there), so covers are fetched via httpx into novels/.covers/
    and the image is given the local path instead. Already-cached covers resolve
    synchronously; otherwise the download happens on the async loop and the
    source is swapped in when it lands."""
    local = _cached_cover(url)
    if local:
        img.source = local
        return

    # Placeholder: opaque surface color while cover downloads.
    from gui.screens.theme import surface_color
    img.color = surface_color()

    async def coro():
        return await _download_cover(url)

    def on_done(path, error):
        if error is None and path:
            img.source = path
            img.color = [1, 1, 1, 1]
            # Fade-in animation.
            from kivy.animation import Animation
            Animation(opacity=1, duration=0.3).start(img)

    async_loop.run(coro(), on_done)


async def _download_novel(source, qualified_slug, chapters, title,
                          total=None, progress_cb=None,
                          translate=False, lang=""):
    """Save every chapter via source.save_chapter (or read+translate when
    *translate* is True), download the cover, and write meta.json with the
    real title + cover file.

    When *translate* is True, each chapter is fetched via source.read_chapter,
    translated with _translate_text(text, lang), and saved as
    {safe_title}_{lang}.txt — the plain English file is skipped so the
    translation is the only local copy.

    Returns (saved, failed): 'failed' counts chapters that could not be
    fetched, so callers can tell a network failure apart from 'already saved'.
    total: full novel chapter count for meta.json (so a partial download does
    not misreport the library size). progress_cb(done, saved) is invoked after
    each chapter is processed.

    Up to 4 chapters are fetched concurrently (bounded by a semaphore) instead
    of one at a time, so network latency for a chapter round-trip doesn't add
    up serially across the whole novel. done/saved are shared counters
    updated as each chapter task completes (order of completion isn't
    necessarily the chapter order, but the counts are the same either way).
    """
    from core.translation import _translate_text
    sem = asyncio.Semaphore(4)
    saved = 0
    failed = 0
    done = 0

    async def _process(ch):
        nonlocal saved, failed, done
        safe_title = ch["title"].replace("/", "-").replace(" ", "_")
        if translate:
            path = os.path.join("novels", qualified_slug,
                                f"{safe_title}_{lang}.txt")
        else:
            path = os.path.join("novels", qualified_slug,
                                safe_title + ".txt")
        if not os.path.exists(path):
            async with sem:
                try:
                    if translate:
                        lines = await source.read_chapter(ch["url"])
                        if not lines:
                            failed += 1
                        else:
                            text = "\n\n".join(lines)
                            translated = await asyncio.to_thread(
                                _translate_text, text, lang)
                            if not translated:
                                failed += 1
                            else:
                                os.makedirs(
                                    os.path.join("novels", qualified_slug),
                                    exist_ok=True)
                                with open(path, "w", encoding="utf-8") as f:
                                    f.write(translated)
                                saved += 1
                    else:
                        if await source.save_chapter(ch["url"], ch["title"],
                                                     qualified_slug):
                            saved += 1
                        else:
                            failed += 1
                except Exception:
                    failed += 1
        done += 1
        if progress_cb is not None:
            progress_cb(done, saved)

    await asyncio.gather(*(_process(ch) for ch in chapters))

    cover_file = await _save_cover(source, qualified_slug)

    try:
        os.makedirs(os.path.join("novels", qualified_slug), exist_ok=True)
        meta = {"title": title, "cover": cover_file,
                "chapters": total or len(chapters)}
        if translate and lang:
            meta["lang"] = lang
        # Merge with existing meta (preserves 'tracked' from _track_novel).
        existing_meta = _read_meta(qualified_slug)
        existing_meta.update(meta)
        with open(os.path.join("novels", qualified_slug, "meta.json"), "w") as f:
            json.dump(existing_meta, f)
    except OSError:
        pass
    return saved, failed


def _open_chapters_for(novel, source, set_loading=None, fallback=None):
    """Shared novel-tap flow: fetch chapters, then goto the chapter list.
    set_loading(bool) optionally toggles a busy state on the caller's view.
    fallback: local chapters to show if the online fetch fails or is empty
    (keeps downloaded novels openable offline)."""
    def _set(state):
        if set_loading:
            set_loading(state)

    if source is None:
        _snack("No source for this novel.")
        _set(False)
        return

    async def coro():
        cover = novel.get("cover", "") or ""
        chapters = None
        try:
            if not cover:
                cover = await source.cover_url(novel["slug"])
            chapters = await _get_chapters(source, novel["slug"])
        except Exception:
            pass
        if not chapters and fallback:
            chapters = fallback
        return chapters, cover

    def on_done(result, error):
        _set(False)
        if error is not None:
            _snack("Failed to fetch chapters. Check your connection.")
            return
        chapters, cover = result
        if not chapters:
            if getattr(source, "blocked", False):
                _snack(f"{source.label} is blocked by anti-bot protection.")
            else:
                _snack("No chapters found.")
        else:
            app = MDApp.get_running_app()
            if app is None:
                return
            app.goto(
                "chapter_list",
                chapters=chapters,
                slug=source.qualify_slug(novel["slug"]),
                source=source,
                title=novel["title"],
                cover=cover,
            )

    _set(True)
    async_loop.run(coro(), on_done, timeout=30)
