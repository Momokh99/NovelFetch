"""Source dispatch helpers shared by both frontends.

These were historically duplicated between the TUI `screens/utils.py` and the
GUI `screens/utils.py`. They depend only on `sources` and the standard library,
so they live here in core as the single source of truth.
"""

import time

from sources import REGISTRY


def _get_source(slug):
    source_name = slug.split(":", 1)[0] if ":" in slug else None
    if source_name:
        return REGISTRY.get(source_name)
    return None


_chapter_cache: dict[str, tuple[float, list[dict[str, object]]]] = {}


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
