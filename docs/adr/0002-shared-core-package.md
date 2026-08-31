# ADR 0002: Consolidate shared modules into core/

## Context

Both frontends (`tui/` and `gui/`) depend on a set of UI-independent modules:
`progress.py` (reading progress + tracking), `translation.py` (Google
Translate), `epub.py` (EPUB export), and the source-dispatch helpers
`_get_source` / `_get_chapters`. These lived as loose top-level modules at the
repo root, and the dispatch helpers were **duplicated** — an identical copy in
each frontend's `utils.py` (the GUI's copy was the functional superset, keying
its chapter cache by source so the same slug could exist across sources).

## Decision

Move the UI-independent modules into a single top-level **`core/`** package:

- `core/progress.py`, `core/translation.py`, `core/epub.py`
- `core/utils.py` — the deduplicated `_get_source` / `_get_chapters`

Both frontends now import from `core.*`. The GUI kept its GUI-specific helpers
(library fingerprinting, cover cache, downloads) in `gui/screens/utils.py`, now
re-importing the shared dispatch helpers from `core.utils`.

## Consequences

- The dispatch-helper duplication is gone; the chapter-cache key includes the
  source name.
- `sources/` remains the single scraper seam; `core` serves both frontends.
- The repo root is no longer littered with single-purpose modules.
