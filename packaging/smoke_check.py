#!/usr/bin/env python3
"""Post-install smoke check for the built distribution.

Run this with the *target* interpreter after installing the wheel into a clean
venv:

    /tmp/novelfetch-venv/bin/python packaging/smoke_check.py

Two things it is careful about:

* **Run it by path from outside the repo root.** A script's own directory lands
  on sys.path, not the current directory, so `packaging/` (which contains no
  `tui`/`sources`) is what gets added and the imports resolve to the installed
  package. Running `python -c "..."` from the repo root instead puts the repo
  first on sys.path and silently checks the source checkout rather than the
  wheel — a check that cannot fail.
* **No dependency on extras.** The TUI dependencies are mandatory, so a bare
  install has to import cleanly. Importing `gui` is deliberately not attempted:
  it needs the `gui` extra and opens a window.
"""

import sys
from pathlib import Path

EXPECTED_SOURCES = {
    "novelfire",
    "novelphoenix",
    "royalroad",
    # NOTE: registered as "scribblehub" (double b), which disagrees with the
    # module name, the site name, and every other spelling in the repo. It looks
    # like a typo, but the key is embedded in persisted slugs
    # ("<source>:<novel>" in progress.json / tracking.json, resolved by
    # core.utils._get_source), so correcting it needs a data migration for
    # existing installs. Do not "fix" this spelling here to make CI pass.
    "scribblehub",
    "wuxiaspot",
}


def main() -> int:
    try:
        import tui  # noqa: F401  (mandatory TUI deps must be installed)
        from sources import REGISTRY
    except ImportError as exc:
        print(f"smoke check failed: bare install cannot import: {exc}", file=sys.stderr)
        return 1

    got = set(REGISTRY)
    if got != EXPECTED_SOURCES:
        print(
            f"smoke check failed: source registry is {sorted(got)}, "
            f"expected {sorted(EXPECTED_SOURCES)}",
            file=sys.stderr,
        )
        return 1

    missing = [
        p
        for p in ("tui/novelfetch.tcss", "gui/kv/reader.kv")
        if not (Path(tui.__file__).parent.parent / p).is_file()
    ]
    if missing:
        print(f"smoke check failed: missing package data: {missing}", file=sys.stderr)
        return 1

    print(f"smoke check ok: {len(got)} sources registered, package data present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
