# NovelFetch

A TUI novel reader with a pluggable source system. Browse, search, download, and read chapters — all in the terminal.

```
     ███╗   ██╗ ██████╗ ██╗   ██╗███████╗██╗     ██████╗ ██╗███╗   ██╗
     ████╗  ██║██╔═══██╗██║   ██║██╔════╝██║     ██╔══██╗██║████╗  ██║
     ██╔██╗ ██║██║   ██║██║   ██║█████╗  ██║     ██████╔╝██║██╔██╗ ██╗
     ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══╝  ██║     ██╔══██╗██║██║╚██╗██║
     ██║ ╚████║╚██████╔╝ ╚████╔╝ ███████╗███████╗██████╔╝██║██║ ╚████║
     ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚══════╝╚══════╝╚═════╝ ╚═╝╚═╝  ╚═══╝
     ════════════════════════════════════════════════════════════════════
                          TUI Novel Reader v2
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

```bash
git clone https://github.com/Momokh99/NovelFetch.git
cd NovelFetch
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install textual httpx beautifulsoup4 deep-translator
python main.py
```

---

## How It Works

**Architecture:**

- `main.py` — `NovelFetchApp` (Textual `App` subclass), entry point
- `sources/` — pluggable Source ABC; RoyalRoad implementation with httpx
- `screens/` — modular screen package: `browse.py`, `reader.py`, `library.py`, `download.py`, `shared.py`, `utils.py`
- `progress.py` — `ProgressTracker`, `_scan_library`, `_slug_to_title`
- `epub.py` — `_export_epub`
- `translation.py` — `_translate_text`
- `novels/` — Downloaded chapters and `progress.json`

---

## Roadmap

- [x] TUI mode (Textual interface)
- [x] Resume from last chapter (progress.json)
- [x] Search with auto-type and pagination
- [x] Translation (Google Translate, 12 languages, RTL support)
- [ ] Better text formatting (italics, line breaks, spacing)
- [ ] Search filters (genre, status, rating)
- [x] Multi-source architecture (RoyalRoad, ScribbleHub, WuxiaSpot)
- [x] Download dialog (All, Range, Translated)
- [x] Offline reading mode
- [ ] Reading history across sessions
- [ ] **Android app (KivyMD)** — cross-platform mobile UI reusing all source modules
  - [ ] Source selection screen (cards for each source)
  - [ ] Search with debounce + pagination
  - [ ] Browse (hot, latest, popular, genres)
  - [ ] Chapter list with read progress checkmarks
  - [ ] Reader screen (prev/next, font size, night mode, translation)
  - [ ] Download dialog (single, all, range, translated)
  - [ ] Library screen (local novels, resume reading)
  - [ ] Settings (dark mode, clear cache)
  - [ ] APK build via Buildozer

---

## Disclaimer

This tool scrapes publicly available content for personal use. Novels belong to their authors and translators. Support them if you can.
