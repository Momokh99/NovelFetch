# ADR 0003: Retire the pytest suite

## Context

NovelFetch carried a `tests/` directory of 26 files (~5,300 lines) covering GUI and
home-grid rendering, reader logic, library bookkeeping, downloader concurrency,
navigation, theming, source parsing, and TUI performance. It ran on every CI push
via `.github/workflows/python-package.yml` and through `make test` / `test-quick` /
`test-android`.

The suite had drifted into a poor trade. It was the only thing standing between a
refactor and a silent regression, but it was also:

- **Slow and brittle in CI.** Two Kivy suites (`test_home_grid_ui.py`,
  `test_settings_switch.py`) failed on every headless run with
  `FBO Initialization failed: Incomplete attachment (36054)`, and two
  `test_tui_performance.py` memory thresholds failed only in larger batches.
- **Costly to keep green**, which showed up as test-side churn: several commits
  touched test fixtures to repair date-flakiness and GUI teardown rather than to
  test product behavior.
- **Inconsistent with how the code is actually verified.** Scraper correctness is
  decided against live sites, not fixtures: NovelFire's chapter counting, the
  NovelPhoenix selectors, and the real browse/search pagination were all settled
  by probing the live HTML. The offline tests could only ever assert that a
  hand-written fixture still parses — they could not tell whether the site had
  changed.

The maintainer chose to ship without the suite rather than keep spending on it.

## Decision

Remove the test suite and every piece of configuration wired to it:

- Delete `tests/` in full, including `conftest.py`.
- `pyproject.toml`: drop the `pytest` / `pytest-cov` dev dependencies, the
  `[tool.pytest.ini_options]` section, the `"tests/**"` ruff per-file-ignores,
  the now-meaningless `"PT"` (flake8-pytest-style) rules, and `"tests/"` from the
  mypy exclude.
- `Makefile`: remove the `test`, `test-quick` and `test-android` targets, the
  `pytest pytest-cov` install in `setup-android`, and `.pytest_cache/` from
  `clean`.
- `.github/workflows/python-package.yml`: remove the `Test with pytest` step and
  the `pytest` install. This one is load-bearing — a bare `pytest` with no
  `testpaths` collects nothing and exits 4, which fails the build.

Lint and type checking are unaffected: `make lint` still runs ruff, mypy and
pyright, and `make format-check` still runs ruff format.

## Consequences

- **No automated regression coverage.** Changes to the scrapers, the reader, the
  library and the TUI are now verified only by running the app. Every fix in this
  area carries its live-verification transcript in the commit body instead of a
  regression test.
- **CI runs faster and goes green**, because the headless Kivy failures are gone
  along with the suites that caused them.
- **Correctness evidence shifts to live verification.** Source changes must be
  checked against the real site; a fixture can drift from the site indefinitely
  without anyone noticing.
- Adding tests back is not a reversal of this decision. If a suite returns, it
  should be scoped to what live probing cannot cover — pure logic such as EPUB
  spine generation or translation — and the CI `Test with pytest` step has to come
  back with it.