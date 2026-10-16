# ADR 0004: Publish to PyPI with Trusted Publishing, TUI-first

## Context

The project already produced a wheel and an sdist — `release.yml` built them and
attached them to the GitHub Release, and the AUR `PKGBUILD` installed them — but
there was no path to PyPI. Publishing was not just a matter of adding an upload
step, because several things blocked it outright:

- `pyproject.toml` declared `requires-python = ">=3.9"` while the `sources/`
  modules use PEP 604 unions (`str | None`) in annotations that are evaluated at
  definition time, so 3.9 raised `TypeError` on import.
- `license = { file = "LICENSE" }` is the pre-PEP 639 table form, deprecated in
  setuptools 77 and unsupported as of 2026-02-18.
- `pyproject.toml` and `buildozer.spec` disagreed on the version, which made
  `packaging/release.py --check` fail and blocked the whole release workflow.
- The `wheel` job's smoke test asserted `len(REGISTRY) == 3` when five sources
  were registered.

A separate question was which frontend to ship. `pyproject.toml` exposed the TUI
behind a `tui` extra, so `pip install novelfetch` produced a TUI that crashed on
`import textual`, while `pip install "novelfetch[gui]"` was the only way to get a
working terminal app. The GUI ships separately as an APK and an AppImage, so the
TUI is the natural PyPI entry point — but the KivyMD desktop GUI is perfectly
installable from a wheel, and dropping it would remove a capability rather than
trim a package.

## Decision

Ship **one distribution**, TUI-first, published with **Trusted Publishing**.

- The TUI is the primary frontend: `textual` and `curl_cffi` moved from the `tui`
  extra into `[project] dependencies`, and the `tui` extra was deleted. A bare
  `pip install novelfetch` yields a working terminal app.
- The KivyMD GUI stays a `gui` extra, so `pip install "novelfetch[gui]"` still
  installs Kivy and gives a working desktop GUI. The `gui` package, its `.kv`
  files, fonts, icon, and the `novelfetch-gui` console script all remain in the
  wheel — nothing about the release pipeline changed as a result.
- `requires-python = ">=3.10"`, and the license moved to PEP 639
  (`license = "MIT"` + `license-files`, with `setuptools>=77.0.3`).
- A dedicated `.github/workflows/pypi-publish.yml` builds and publishes the
  distribution using `pypa/gh-action-pypi-publish` with
  `permissions: id-token: write`. No API token is stored in the repository.
  It is separate from `release.yml` so a publish never waits on the APK, AppImage,
  and Windows jobs.
- Because PyPI versions are immutable, **tag pushes publish to TestPyPI**. A
  release is promoted to PyPI by dispatching the workflow manually on the same
  tag. Publishing the same commit to TestPyPI first costs nothing and proves the
  trusted publisher is wired correctly.

`curl_cffi` stays a mandatory dependency even though `sources/scriblehub.py`
imports it lazily and degrades to httpx. It is a ~13 MB wheel, but that fallback
means a source silently stops working rather than the install staying small.

## Consequences

- **One wheel serves every consumer.** Android (buildozer `source.dir = .`), the
  Windows binaries, the AppImage, the AUR package, and PyPI all build from the same
  tree, so there is no second distribution to keep in sync.
- **The install exposes generic top-level module names** — `core`, `tui`, `gui`,
  `sources` land in `site-packages` and can collide with unrelated packages. The
  PyPI project name was still free when this was written, so restructuring under a
  `novelfetch/` namespace remained available; it was declined as import churn
  across ~156 sites for a packaging preference.
- **A default `pip install` is heavier than before** (~13 MB more, for
  `curl_cffi`), and the Windows release job installs `.` rather than `.[tui]`.
- **TestPyPI-then-PyPI is two steps per release.** Deliberate: it is the cheapest
  rehearsal available for an irreversible publish. Once the process is trusted,
  changing the `environment` expression in `pypi-publish.yml` to send tag pushes
  straight to `pypi` collapses it back to one step.
- The publish workflow depends on two GitHub environments (`pypi`, `testpypi`)
  being configured as trusted publishers on the matching PyPI accounts. That is
  manual, one-time, and undocumented anywhere except the workflow's own header
  comment and this ADR.