# NovelFetch

A terminal + mobile novel reader with a pluggable source system. Browse, search, download, and read chapters.

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

---

## Features

- **Search** — real-time search with 750ms debounce; paginate with `n`/`p`
- **Browse** — hot, latest, most popular, completed, and 10 genres
- **My Library** — browse locally downloaded novels, resume reading, delete
- **Reader** — next/prev (`n`/`p`), jump to chapter (`j`), download current (`d`)
- **Progress tracking** — auto-saves last chapter; ✓ marks read chapters
- **Download dialog** — All, Range, or Translated; progress bar with translation warning
- **Translation** — Google Translate (12 languages); Arabic RTL layout
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
- `core/` — shared framework: `progress.py`, `translation.py`, `epub.py`, `utils.py` (source dispatch)
- `sources/` — pluggable Source interface; RoyalRoad, ScribbleHub, WuxiaSpot implementations
- `novels/` — Downloaded chapters and `progress.json`

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
- [ ] Better text formatting (italics, line breaks, spacing)
- [ ] Search filters (genre, status, rating)
- [ ] APK build via Buildozer

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

### Development Tools

- **Linting**: Ruff (replaces flake8/black/isort)
- **Type Checking**: Mypy + Pyright
- **Testing**: Pytest with coverage
- **Pre-commit**: Auto-format on commit

---

## Disclaimer

This tool scrapes publicly available content for personal use only. Novels belong to their authors and translators. Do not redistribute downloaded content. Support the creators if you enjoy their work.
