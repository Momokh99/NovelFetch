# ADR 0001: Split frontends into tui/ and gui/

## Context

NovelFetch ships two frontends that share one framework: a Textual **TUI** and a
KivyMD **GUI** (desktop + Android). Both historically used a top-level package
named `screens` — the TUI's `screens/` at the repo root and the GUI's
`screens/` under `android_app/`. This name collision forced fragile path
precedence hacks: `tests/conftest.py` had to insert `android_app` before the
repo root so that a bare `from screens import ...` resolved to the Kivy screens,
and `pyrightconfig.json` encoded the same ordering so each environment pointed
at the right package. Any change to the import order silently switched which
frontend a `screens` import resolved to.

## Decision

Give each frontend its own top-level package, eliminating the collision:

- `screens/` (Textual TUI) → **`tui/`**
- `android_app/` (KivyMD GUI) → **`gui/`**, with its screens at `gui/screens/`

Every import was rewritten to the fully-qualified `tui.*` / `gui.screens.*`
paths, and the KV `#:import` tokens (`screens.theme`, `screens.home_tab`) became
`gui.screens.*`. The `conftest.py` precedence hack is gone; tests and type
checking now resolve each package unambiguously.

## Consequences

- The bare `screens` name collision and its path-ordering hacks are removed.
- Imports are self-documenting: `tui.*` and `gui.screens.*` make the frontend
  explicit.
- The root `main.py` stays a thin dispatcher: TUI on desktop, GUI when packaged
  for Android (via `ANDROID_ARGUMENT`).
