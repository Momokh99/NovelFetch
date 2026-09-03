"""Download orchestrator — shared by both GUI and TUI.

This module replaces the duplicated download logic that previously lived in
:mod:`gui.screens.utils` (``_download_novel``) and :mod:`tui.download`
(``DownloadProgressScreen._download_all``).  It owns the concurrent
semaphore, chapter‑by‑chapter orchestration, progress reporting, and the
final metadata/cover write‑back.

The public API is a single async function:

    await download(source, qualified_slug, chapters, title, ...)

which returns ``(saved, failed)`` — exactly matching the signatures that
callers currently expect.
"""

import asyncio
import os
from typing import Optional

from core.library import (
    chapter_path,
    delete_library,
    has_chapters,
    local_chapters,
    local_chapter_count,
    missing_chapters,
    read_meta,
    scan_library,
    translated_path,
    write_chapter,
    write_meta,
)


async def download(
    source,
    qualified_slug,
    chapters,
    title,
    *,
    translate=False,
    lang="",
    total=None,
    progress_cb=None,
    base_dir=None,
) -> tuple[int, int]:
    """Download every chapter of a novel and persist the results.

    Parameters
    ----------
    source : Source
        The scraper source providing ``read_chapter`` (and ``cover_url`` if
        a cover is needed).
    qualified_slug : str
        The source-qualified slug, e.g. ``royalroad:some-title``.
    chapters : list[dict]
        Chapter entries as returned by :func:`core.utils._get_chapters`.
    title : str
        Novel title (written into meta.json).
    translate : bool
        When True, each chapter is fetched via :func:`source.read_chapter`,
        then translated with :func:`core.translation._translate_text`.
    lang : str
        Translation language code (e.g. ``"ar"``).
    total : int, optional
        Total chapter count for meta.json.  Defaults to ``len(chapters)``.
    progress_cb : callable, optional
        ``progress_cb(done, saved)`` is called after each chapter completes.
    base_dir : str, optional
        Root of the novels directory.  Defaults to the process working
        directory (matching historic ``CWD``-relative behaviour).

    Returns
    -------
    (saved, failed) : tuple[int, int]
        *saved* counts chapters that were successfully fetched/saved;
        *failed* counts chapters that could not be fetched.
    """
    novels_dir = os.path.join(base_dir or os.getcwd(), "novels")
    total = total or len(chapters)
    saved = 0
    failed = 0
    done = 0

    sem = asyncio.Semaphore(4)

    async def _process(ch):
        nonlocal saved, failed, done
        safe_title = ch["title"].replace("/", "-").replace(" ", "_")
        # Determine the file path for this chapter
        if translate:
            path = os.path.join(novels_dir, qualified_slug,
                                f"{safe_title}_{lang}.txt")
        else:
            path = os.path.join(novels_dir, qualified_slug,
                                f"{safe_title}.txt")

        # Skip if the chapter file already exists (preserves "already
        # downloaded" behaviour from the former GUI _download_novel).
        if os.path.exists(path):
            done += 1
            if progress_cb is not None:
                progress_cb(done, saved)
            return

        async with sem:
            try:
                if translate:
                    lines = await source.read_chapter(ch["url"])
                    if not lines:
                        failed += 1
                    else:
                        text = "\n\n".join(lines)
                        # Translate using the shared core.translation helper.
                        # Import inside the function to avoid triggering the
                        # module-level deep_translator dependency.
                        try:
                            from core.translation import _translate_text as _tt
                            translated = _tt(text, target=lang)
                        except (ImportError, ModuleNotFoundError):
                            translated = text
                        if not translated:
                            failed += 1
                        else:
                            os.makedirs(os.path.join(novels_dir, qualified_slug),
                                        exist_ok=True)
                            with open(path, "w", encoding="utf-8") as f:
                                f.write(translated)
                            saved += 1
                else:
                    lines = await source.read_chapter(ch["url"])
                    if not lines:
                        failed += 1
                    else:
                        text = "\n\n".join(lines)
                        write_chapter(qualified_slug, ch["title"], text,
                                            lang=None, base_dir=base_dir)
                        saved += 1
            except Exception:
                failed += 1
        done += 1
        if progress_cb is not None:
            progress_cb(done, saved)

    await asyncio.gather(*(_process(ch) for ch in chapters))

    # ---- completion: write meta.json + cover ----
    # Build meta
    try:
        cover = await source.cover_url(qualified_slug.split(":")[-1] if ":" in qualified_slug else qualified_slug)
    except Exception:
        cover = ""
    meta = {"title": title, "cover": cover}
    if translate and lang:
        meta["lang"] = lang
    meta["chapters"] = total
    # Merge with existing meta (preserves 'tracked' from prior tracking)
    existing_meta = read_meta(qualified_slug, base_dir)
    existing_meta.update(meta)
    write_meta(qualified_slug, existing_meta, base_dir)

    return saved, failed