"""Library persistence store — owns all file operations under novels/.

This module replaces the former scattered implementation in
gui/screens/utils.py and core/progress.py. Every function accepts an
optional ``base_dir`` parameter; when omitted it defaults to the process
working directory (matching the historic CWD-relative behaviour so
existing callers and tests continue to work unchanged).

All paths are relative to the novels directory::

    novels_dir = os.path.join(base_dir or os.getcwd(), "novels")

The :func:`data_dir <core.paths.data_dir>` function from :mod:`core.paths`
can be used to obtain the app's data root (the directory the app chdir's
into at startup via ``ensure_data_dir``).
"""

import json
import os
import re
import shutil
from typing import Optional

from core.progress import _is_translation_file

NOVELS_DIR = "novels"


def _novels_dir(base_dir=None):
    """Return the path to the novels directory."""
    if base_dir is not None:
        return os.path.join(base_dir, NOVELS_DIR)
    return os.path.join(os.getcwd(), NOVELS_DIR)


def read_meta(slug, base_dir=None):
    """Per-novel meta.json: {"title": ..., "cover": "...", ...} or {}."""
    path = os.path.join(_novels_dir(base_dir), slug, "meta.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def write_meta(slug, meta, base_dir=None):
    """Persist meta.json for a novel."""
    path = os.path.join(_novels_dir(base_dir), slug, "meta.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def meta_lang(slug, base_dir=None):
    """Return the saved translation language code for a novel, or None."""
    return read_meta(slug, base_dir).get("lang")


def read_last_updated(slug, base_dir=None):
    """Unix timestamp of the last update check that found new chapters, or 0."""
    return int(read_meta(slug, base_dir).get("last_updated") or 0)


def write_last_updated(slug, ts, base_dir=None):
    """Persist the last-updated timestamp into the novel's meta.json."""
    meta = dict(read_meta(slug, base_dir))
    meta["last_updated"] = int(ts)
    write_meta(slug, meta, base_dir)


def update_chapters_meta(slug, count, ts, base_dir=None):
    """Update meta.json with the source's total chapter count and a timestamp."""
    meta = dict(read_meta(slug, base_dir))
    meta["chapters"] = int(count)
    meta["last_updated"] = int(ts)
    write_meta(slug, meta, base_dir)


def _chapter_sort_key(fname):
    nums = re.findall(r"\d+", fname)
    return int(nums[0]) if nums else 0


def local_chapters(slug, base_dir=None):
    """Build a chapter list from the downloaded novels/{slug}/*.txt files.

    Translation-suffixed files ({title}_{lang}.txt) are excluded so chapter
    counts and indices stay canonical."""
    chap_dir = os.path.join(_novels_dir(base_dir), slug)
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


def local_chapter_count(slug, base_dir=None):
    """Distinct downloaded chapters for a novel, counting the novel's own
    translation-language files as real chapters (so an update check does not
    re-report them as new). Canonical and translated copies of the same
    chapter count once."""
    chap_dir = os.path.join(_novels_dir(base_dir), slug)
    if not os.path.isdir(chap_dir):
        return 0
    lang = _meta_lang(slug, base_dir)
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


def has_chapters(slug, base_dir=None):
    """True if any downloaded chapter .txt exists under novels/{slug}."""
    path = os.path.join(_novels_dir(base_dir), slug)
    if not os.path.isdir(path):
        return False
    return any(name.endswith(".txt") and _is_translation_file(name) is None
               for name in os.listdir(path))


def missing_chapters(chapters, slug, lang, base_dir=None):
    """Return chapters whose local file is not present under novels/{slug}."""
    lang = lang or ""
    chap_dir = os.path.join(_novels_dir(base_dir), slug)
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


def display_title(slug, fallback, base_dir=None):
    """Clean novel title for UI display: prefer meta title, then strip
    the numeric id-prefix from slug-derived fallbacks (e.g. '136609/Ashland'
    → 'Ashland')."""
    meta_title = read_meta(slug, base_dir).get("title")
    if meta_title and not re.match(r"^\d+/", meta_title):
        return meta_title
    raw = slug.split(":", 1)[-1] if ":" in slug else slug
    if re.match(r"^\d+/", raw):
        raw = raw.split("/", 1)[1]
    return raw.replace("-", " ").title()


def is_tracked(slug, base_dir=None):
    """True if a slug is registered as tracked, via meta.json or the
    tracking registry (which persists even after the folder is deleted)."""
    from core.progress import progress
    meta = read_meta(slug, base_dir)
    return bool(meta.get("tracked")) or progress.is_tracked(slug)


def library_entries(base_dir=None):
    """Every library novel: folders on disk plus tracked-but-deleted slugs.

    Each entry: {slug, title, count, tracked} — tracked slugs whose files are
    gone still show up so the reader can re-add/update them."""
    novels_dir = _novels_dir(base_dir)
    entries = _scan_library(novels_dir)
    seen = {n["slug"] for n in entries}
    from core.progress import progress
    for t in progress.tracked_novels():
        if t["slug"] not in seen:
            entries.append({"slug": t["slug"], "title": t["title"], "count": 0})
    entries.sort(key=lambda n: n["slug"])
    return entries


def _library_sig_rows(entries):
    """Per-folder (slug, count, dir_mtime, top_mtime) rows used by
    library_fingerprint() instead of walking novels/ again."""
    novels_dir = "novels"
    sig = []
    for n in entries:
        slug = n["slug"]
        folder = os.path.join("novels", slug)
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


def library_entries_and_fingerprint(base_dir=None):
    """Single-pass version of library_entries() + library_fingerprint():
    scans the novels/ tree once and derives both from it, instead of two
    independent full-tree walks back to back."""
    from core.progress import progress
    entries = library_entries(base_dir)
    sig = _library_sig_rows(entries)
    try:
        from core.paths import data_dir
        prog_mtime = round(os.path.getmtime(data_dir()), 6)
    except Exception:
        prog_mtime = -1.0
    return entries, repr((sig, prog_mtime))


def library_fingerprint(base_dir=None):
    """Cheap signature of everything the library views depend on: the
    novels/ tree (per-folder chapter counts + dir and meta/cover mtimes)
    and progress.json (tracked/read state).

    Equal fingerprints ⇒ the on-screen library is up to date, so callers can
    skip rebuilding widget trees."""
    _, fp = library_entries_and_fingerprint(base_dir)
    return fp


def delete_library(slug, untrack=False, base_dir=None):
    """Remove a novel's files and its reading progress. Tracking survives by
    default so the novel stays in the library (tracked-only) and can be
    re-downloaded; pass untrack=True for a full removal."""
    novels_dir = _novels_dir(base_dir)
    shutil.rmtree(os.path.join(novels_dir, slug), ignore_errors=True)
    from core.progress import progress
    progress.remove(slug)
    if untrack:
        progress.untrack(slug)
    progress.flush()


def track(slug, title, base_dir=None):
    """Register a slug as tracked. Persists even if the novels/{slug}
    folder is removed, so tracking survives deleting the files."""
    from core.progress import progress
    progress.track(slug, title)


def untrack(slug, base_dir=None):
    """Stop tracking a novel (keeps any reading progress)."""
    from core.progress import progress
    progress.untrack(slug)


def is_tracked_base(slug, base_dir=None):
    """True if a slug is registered as tracked via the tracking registry."""
    from core.progress import progress
    return progress.is_tracked(slug)


def _scan_library(base_dir=None):
    """Scan the novels/ directory and return a list of novel entries.

    Each entry is a dict with keys ``slug``, ``title``, and ``count``.
    """
    novels_dir = _novels_dir(base_dir)
    if not os.path.isdir(novels_dir):
        return []
    result = []
    for root, dirs, files in os.walk(novels_dir):
        if "meta.json" not in files:
            continue
        rel = os.path.relpath(root, novels_dir).replace(os.sep, "/")
        count = sum(1 for f in files
                    if f == "meta.json" or
                    (f.endswith(".txt") and _is_translation_file(f) is None) or
                    (not f.endswith(".txt") and not f.endswith(".tmp")))
        result.append({"slug": rel, "title": _slug_to_title(rel), "count": count})
    result.sort(key=lambda n: n["slug"])
    return result


def _slug_to_title(slug):
    raw = slug.split(":", 1)[-1] if ":" in slug else slug
    return raw.replace("-", " ").title()


def _is_translation_file(fname):
    """Return the lang code if *fname* is a translation file, else None."""
    m = re.match(r"^(.+)_([a-z]{2}(?:-[a-z]{2})?)\.txt$", fname)
    if m and m.group(2) in {"ar", "en", "fr", "de", "es", "it", "ja", "zh", "ru", "pt", "tr", "hi", "nl", "pl", "vi", "th", "id", "ms"}:
        return m.group(2)
    return None


def _meta_lang(slug, base_dir=None):
    """Return the saved translation language code for a novel, or None."""
    return read_meta(slug, base_dir).get("lang")


def translated_path(chapter_title, slug, lang, base_dir=None):
    """Return the local path for a translated chapter file, or ''."""
    if not lang:
        return ""
    safe = chapter_title.replace("/", "-").replace(" ", "_")
    return os.path.join(_novels_dir(base_dir), slug, f"{safe}_{lang}.txt")


def chapter_path(chapter_title, slug, lang=None, base_dir=None):
    """Return the local path for a chapter file."""
    if lang:
        return translated_path(chapter_title, slug, lang, base_dir)
    return os.path.join(_novels_dir(base_dir), slug,
                        f"{chapter_title.replace('/', '-').replace(' ', '_')}.txt")


def write_chapter(slug, title, content, lang=None, base_dir=None):
    """Write a chapter file under novels/{slug}/. Returns True on success.

    If *lang* is given the file is saved as ``{safe_title}_{lang}.txt``; otherwise
    as ``{safe_title}.txt``."""
    novels_dir = _novels_dir(base_dir)
    safe_title = title.replace("/", "-").replace(" ", "_")
    if lang:
        path = os.path.join(novels_dir, slug, f"{safe_title}_{lang}.txt")
    else:
        path = os.path.join(novels_dir, slug, f"{safe_title}.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def scan_library(base_dir=None):
    """Deprecated alias for library_entries(). Kept for backward compatibility."""
    return library_entries(base_dir)


def is_translation_file(fname):
    """Return the lang code if *fname* is a translation file, else None."""
    return _is_translation_file(fname)


_async_http_client = None


def _get_http_client():
    global _async_http_client
    if _async_http_client is None:
        import httpx
        _async_http_client = httpx.AsyncClient(follow_redirects=True, timeout=30)
    return _async_http_client


async def save_cover(source, qualified_slug, base_dir=None):
    """Download the novel cover into novels/{qualified_slug}/, return filename."""
    raw = qualified_slug.split(":", 1)[-1] if ":" in qualified_slug else qualified_slug
    novels_dir = _novels_dir(base_dir)
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
        cover_dir = os.path.join(novels_dir, qualified_slug)
        os.makedirs(cover_dir, exist_ok=True)
        with open(os.path.join(cover_dir, name), "wb") as f:
            f.write(resp.content)
        return name
    except Exception:
        return ""