from sources import REGISTRY
import re
import shutil
import time
import json
import os

from kivymd.app import MDApp
from kivymd.uix.button import MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.snackbar import MDSnackbar

from async_runner import async_loop


def _snack(text):
    """KivyMD 1.2.0 MDSnackbar takes child widgets, not a text kwarg."""
    MDSnackbar(MDLabel(text=text)).open()


def _chapter_sort_key(fname):
    nums = re.findall(r"\d+", fname)
    return int(nums[0]) if nums else 0


def _local_chapters(slug):
    """Build a chapter list from the downloaded novels/{slug}/*.txt files."""
    chap_dir = os.path.join("novels", slug)
    if not os.path.isdir(chap_dir):
        return []
    files = [f for f in os.listdir(chap_dir) if f.endswith(".txt")]
    files.sort(key=_chapter_sort_key)
    chapters = []
    for i, f in enumerate(files, 1):
        title = os.path.basename(f).replace(".txt", "").replace("_", " ").title()
        chapters.append({"num": i, "title": title, "url": ""})
    return chapters


def _delete_library(slug, untrack=False):
    """Remove a novel's files and its reading progress. Tracking survives by
    default so the novel stays in the library (tracked-only) and can be
    re-downloaded; pass untrack=True for a full removal."""
    from progress import progress
    shutil.rmtree(os.path.join("novels", slug), ignore_errors=True)
    progress.remove(slug)
    if untrack:
        progress.untrack(slug)
    progress.flush()


def _get_source(slug):
    source_name = slug.split(":", 1)[0] if ":" in slug else None
    if source_name:
        return REGISTRY.get(source_name)
    return None


_chapter_cache: dict[str, tuple[float, list[dict]]] = {}

async def _get_chapters(source, slug, ttl=300):
    now = time.monotonic()
    # Cache key includes the source: the same slug can exist across sources.
    key = f"{source.name}:{slug}"
    cached = _chapter_cache.get(key)
    if cached and now - cached[0] < ttl:
        return cached[1]
    chapters = await source.fetch_chapters(slug)
    _chapter_cache[key] = (now, chapters)
    return chapters


def _read_meta(slug):
    """Per-novel meta.json: {"title": ..., "cover": "cover.jpg"} or {}."""
    try:
        with open(os.path.join("novels", slug, "meta.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _has_chapters(slug):
    """True if any downloaded chapter .txt exists under novels/{slug}."""
    path = os.path.join("novels", slug)
    if not os.path.isdir(path):
        return False
    return any(name.endswith(".txt") for name in os.listdir(path))


def _is_tracked(slug):
    """True if a slug is registered as tracked, via meta.json or the
    tracking registry (which persists even after the folder is deleted)."""
    from progress import progress
    return bool(_read_meta(slug).get("tracked")) or progress.is_tracked(slug)


def _library_entries():
    """Every library novel: folders on disk plus tracked-but-deleted slugs.

    Each entry: {slug, title, count, tracked} — tracked slugs whose files are
    gone still show up so the reader can re-add/update them."""
    from progress import _scan_library, progress
    entries = _scan_library()
    seen = {n["slug"] for n in entries}
    for t in progress.tracked_novels():
        if t["slug"] not in seen:
            entries.append({"slug": t["slug"], "title": t["title"], "count": 0})
    entries.sort(key=lambda n: n["slug"])
    return entries


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
    from progress import progress
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
        root = MDApp.get_running_app().root
        if hasattr(root, "homescreen_library_refresh"):
            root.homescreen_library_refresh()

    btn.disabled = True
    async_loop.run(coro(), on_done)


async def _save_cover(source, qualified_slug):
    """Download the novel cover into novels/{qualified_slug}/, return filename."""
    raw = qualified_slug.split(":", 1)[-1] if ":" in qualified_slug else qualified_slug
    try:
        url = await source.cover_url(raw)
        if not url:
            return ""
        import httpx
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
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
    """httpx-download a remote cover into the shared cache dir (once)."""
    path = _cover_cache_path(url)
    if not path or (path and os.path.exists(path)):
        return path
    import httpx
    try:
        os.makedirs(_COVER_CACHE_DIR, exist_ok=True)
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return ""
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(resp.content)
        os.replace(tmp, path)
        return path
    except Exception:
        return ""


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

    async def coro():
        return await _download_cover(url)

    def on_done(path, error):
        if error is None and path:
            img.source = path

    async_loop.run(coro(), on_done)


async def _download_novel(source, qualified_slug, chapters, title,
                          total=None, progress_cb=None):
    """Save every chapter via source.save_chapter, download the cover, and
    write meta.json with the real title + cover file.

    Returns (saved, failed): 'failed' counts chapters that could not be
    fetched, so callers can tell a network failure apart from 'already saved'.
    total: full novel chapter count for meta.json (so a partial download does
    not misreport the library size). progress_cb(done, saved) is invoked after
    each chapter is processed."""
    saved = 0
    failed = 0
    for i, ch in enumerate(chapters):
        safe_title = ch["title"].replace("/", "-").replace(" ", "_")
        path = os.path.join("novels", qualified_slug, safe_title + ".txt")
        if os.path.exists(path):
            continue
        try:
            if await source.save_chapter(ch["url"], ch["title"], qualified_slug):
                saved += 1
            else:
                failed += 1
        except Exception:
            failed += 1
        if progress_cb is not None:
            progress_cb(i + 1, saved)

    cover_file = await _save_cover(source, qualified_slug)

    try:
        os.makedirs(os.path.join("novels", qualified_slug), exist_ok=True)
        meta = {"title": title, "cover": cover_file, "chapters": total or len(chapters)}
        with open(os.path.join("novels", qualified_slug, "meta.json"), "w") as f:
            json.dump(meta, f)
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
            MDApp.get_running_app().goto(
                "chapter_list",
                chapters=chapters,
                slug=source.qualify_slug(novel["slug"]),
                source=source,
                title=novel["title"],
                cover=cover,
            )

    _set(True)
    async_loop.run(coro(), on_done)
