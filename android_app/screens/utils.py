from sources import REGISTRY
import time


def _get_source(slug):
    source_name = slug.split(":", 1)[0] if ":" in slug else None
    if source_name:
        return REGISTRY.get(source_name)
    return None


_chapter_cache: dict[str, tuple[float, list[dict]]] = {}

async def _get_chapters(source, slug, ttl=300):
    now = time.monotonic()
    cached = _chapter_cache.get(slug)
    if cached and now - cached[0] < ttl:
        return cached[1]
    chapters = await source.fetch_chapters(slug)
    _chapter_cache[slug] = (now, chapters)
    return chapters
