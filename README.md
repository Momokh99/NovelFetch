# NovelFetch

A terminal + mobile novel reader and downloader with a pluggable scraper architecture. Browse, search, download, translate, and read chapters offline. Ships two frontends over one shared framework: a **Textual TUI** for the terminal and a **KivyMD GUI** for desktop + Android.

```
     ███╗   ██╗ ██████╗ ██╗   ██╗███████╗██╗     ██████╗ ██╗███╗   ██╗
     ████╗  ██║██╔═══██╗██║   ██║██╔════╝██║     ██╔══██╗██║████╗  ██║
     ██╔██╗ ██║██║   ██║██║   ██║█████╗  ██║     ██████╔╝██║██╔██╗ ██║
     ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══╝  ██║     ██╔══██╗██║██║╚██╗██║
     ██║ ╚████║╚██████╔╝ ╚████╔╝ ███████╗███████╗██████╔╝██║██║ ╚████║
     ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚══════╝╚══════╝╚═════╝ ╚═╝╚═╝  ╚═══╝
     ════════════════════════════════════════════════════════════════════
                          TUI + GUI Novel Reader v2
```

![menu](https://img.shields.io/badge/built%20with-Textual-blue)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Search** — real-time search with 750ms debounce; paginate with `n`/`p`
- **Browse** — hot, latest, most popular, completed, and dozens of genres per source
- **My Library** — browse locally downloaded novels, resume reading, delete
- **Reader** — next/prev (`n`/`p`), jump to chapter (`j`), download current (`d`)
- **Progress tracking** — auto-saves last chapter; ✓ marks read chapters
- **Download dialog** — All, Range, or Translated; progress bar with translation warning
- **Translation** — Google Translate (12 languages); Arabic RTL layout with shaped text
- **EPUB export** — generate EPUB files from downloaded chapters
- **Delete with safety** — double-press `x` to confirm deletion

Key bindings in the reader:

| Key | Action |
| ----- | -------- |
| `n` / `p` | Next / Prev chapter |
| `j` | Jump to chapter number |
| `d` | Download dialog (All / Range / Translated) |
| `t` | Translate to language |
| `r` | Revert to original text |
| `h` | Go to main menu |
| `q` | Back to chapter list |

---

## Two frontends, one core

- `main.py` — entry-point dispatcher: TUI on desktop, GUI on Android (`ANDROID_ARGUMENT`).
- `tui/` — **Textual TUI**: `main.py` (app), `main_menu.py`, `browse.py`, `reader.py`, `library.py`, `download.py`, `shared.py`, `utils.py`, `novelfetch.tcss`.
- `gui/` — **KivyMD GUI** (desktop + Android): `main.py`, `screens/` (home, browse, reader, chapter list, download picker/dialog, library, settings, history, update, search), `kv/` layout files, `data/` (icon, bundled Arabic font).
- `core/` — shared framework: `progress.py`, `translation.py`, `epub.py`, `utils.py` (source dispatch), `paths.py` (data-dir resolution for frozen/AppImage/Android).
- `sources/` — pluggable `Source` interface (`base.py`) and a `REGISTRY` of scrapers.
- `novels/` — downloaded chapters, `progress.json`, `tracking.json`, cover cache.

## Pluggable sources

The `Source` abstraction (`sources/base.py:1`) defines browsing, search, chapter fetching, and cover resolution; implementations are registered in `sources/__init__.py:5`:

| Source | Browse lists | Genres | Notes |
|--------|-------------|--------|-------|
| **RoyalRoad** | 8 (hot, popular, latest, newest, completed, rising stars, ongoing, more) | 13 | AJAX-free chapter table |
| **ScribbleHub** | 3 | 26 | Cloudflare-aware; lazy `curl_cffi` with httpx fallback (p4a-safe) |
| **WuxiaSpot** | — | 41 | AJAX pagination (`fy.php`); search marked unreliable |

New sources implement the same interface and register a key — no frontend changes needed.

---

## Installation

### Quick start

```bash
git clone https://github.com/Momokh99/NovelFetch.git
cd NovelFetch
make setup          # creates both environments (TUI + GUI)
make pre-commit-install
```

### Running

```bash
make run-tui        # Textual TUI (terminal)
make run-kivy       # KivyMD GUI (desktop)
```

### What `make setup` does

The project uses two separate virtual environments:

| Environment | Purpose | Created by |
|-------------|---------|------------|
| `myenv/` | TUI + code quality tools (Ruff, mypy, Pyright) | `make setup-tui` |
| `android_env/` | KivyMD GUI + tests | `make setup-android` |

Dependencies are split across `pyproject.toml` optional groups:
- **Core**: `httpx`, `beautifulsoup4`, `deep-translator`, `ebooklib`
- **TUI**: `textual`, `curl_cffi`
- **GUI**: `kivy`, `kivymd`, `arabic-reshaper`, `python-bidi`

---

## How It Works

**Architecture:**

- `main.py` — entry-point dispatcher (TUI or GUI; defaults to TUI on desktop, GUI on Android)
- `tui/` — Textual TUI frontend: `main.py` (app), `main_menu.py`, `browse.py`, `reader.py`, `library.py`, `download.py`, `shared.py`, `utils.py`, `novelfetch.tcss`
- `gui/` — KivyMD GUI frontend (desktop + Android): `main.py`, `screens/` (browse, reader, chapter list, download, library, settings, history), `kv/`, `data/`
- `core/` — shared framework: `progress.py`, `translation.py`, `epub.py`, `utils.py` (source dispatch), `paths.py`
- `sources/` — pluggable Source interface; RoyalRoad, ScribbleHub, WuxiaSpot implementations
- `novels/` — Downloaded chapters and `progress.json`

The GUI is the richer frontend: a 5-tab `MDNavigationBar` (Home / Update / Search / History / Settings) plus per-novel browse flow. Settings persist to `app_settings.json`; update checks reconcile against `update_results.json`. Downloads run concurrently (semaphore 4) with a live progress bar.

---

## Android packaging

`buildozer.spec` builds a debug APK with python-for-android:

- arm64-v8a, API 34 (min 21), NDK 25b
- p4a pinned to `v2026.05.09` (avoids nightly-master breakage with pip ≥ 26)
- CI (`release.yml`) builds and publishes the APK with every tagged release

```bash
make android-debug    # build debug APK
make android-deploy   # deploy to connected device
```

---

## Roadmap

- [x] TUI mode (Textual interface)
- [x] GUI mode (KivyMD desktop + Android)
- [x] Resume from last chapter (progress.json)
- [x] Search with auto-type and pagination
- [x] Translation (Google Translate, 12 languages, RTL support)
- [x] Multi-source architecture (RoyalRoad, ScribbleHub, WuxiaSpot)
- [x] Download dialog (All, Range, Translated)
- [x] Offline reading mode
- [x] Reading history across sessions
- [x] EPUB export
- [x] APK build via Buildozer
- [ ] Better text formatting (italics, line breaks, spacing)
- [ ] Search filters (genre, status, rating)
- [ ] Wire up the remaining preview read-progress styles (5 of 12 are preview-only)

---

## Development

### Quick Start

```bash
# One-time setup
make setup
make pre-commit-install

# Daily development
make run-kivy-dev        # Hot-reload KivyMD desktop
make lint                # Check code quality
make test                # Run test suite
```

### Available Commands

| Command | Description |
|---------|-------------|
| `make setup` | Create both venvs and install all dependencies |
| `make run-tui` | Run TUI app (myenv) |
| `make run-kivy` | Run KivyMD GUI app (android_env) |
| `make lint` | Run Ruff + mypy + Pyright |
| `make format` | Auto-format code |
| `make test` | Run test suite with coverage |
| `make android-debug` | Build debug APK |
| `make android-deploy` | Deploy to connected device |
| `make bump-release VERSION=x.y.z` | Bump version in pyproject.toml + buildozer.spec |

### Development Tools

- **Linting**: Ruff (replaces flake8/black/isort)
- **Type Checking**: Mypy + Pyright
- **Testing**: Pytest with coverage (273 tests)
- **Pre-commit**: Auto-format on commit

---

## Disclaimer

This tool scrapes publicly available content for personal use only. Novels belong to their authors and translators. Do not redistribute downloaded content. Support the creators if you enjoy their work.