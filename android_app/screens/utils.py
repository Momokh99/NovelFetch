from sources import REGISTRY
import time
import json
import os

from kivymd.app import MDApp
from kivymd.uix.snackbar import MDSnackbar

from async_runner import async_loop


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


async def _download_novel(source, qualified_slug, chapters, title):
    """Save every chapter via source.save_chapter, download the cover, and
    write meta.json with the real title + cover file.
    Returns (saved, failed): 'failed' counts chapters that could not be
    fetched, so callers can tell a network failure apart from 'already saved'."""
    saved = 0
    failed = 0
    for ch in chapters:
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

    cover_file = await _save_cover(source, qualified_slug)

    try:
        os.makedirs(os.path.join("novels", qualified_slug), exist_ok=True)
        meta = {"title": title, "cover": cover_file, "chapters": len(chapters)}
        with open(os.path.join("novels", qualified_slug, "meta.json"), "w") as f:
            json.dump(meta, f)
    except OSError:
        pass
    return saved, failed


def _open_chapters_for(novel, source, set_loading=None):
    """Shared novel-tap flow: fetch chapters, then goto the chapter list.
    set_loading(bool) optionally toggles a busy state on the caller's view."""
    def _set(state):
        if set_loading:
            set_loading(state)

    if source is None:
        MDSnackbar(text="No source for this novel.").open()
        _set(False)
        return

    async def coro():
        cover = novel.get("cover", "") or ""
        if not cover:
            try:
                cover = await source.cover_url(novel["slug"])
            except Exception:
                cover = ""
        return await _get_chapters(source, novel["slug"]), cover

    def on_done(result, error):
        _set(False)
        if error is not None:
            MDSnackbar(text="Failed to fetch chapters. Check your connection.").open()
            return
        chapters, cover = result
        if not chapters:
            if getattr(source, "blocked", False):
                MDSnackbar(text=f"{source.label} is blocked by anti-bot protection.").open()
            else:
                MDSnackbar(text="No chapters found.").open()
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
