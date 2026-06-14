# NovelFetch

A TUI novel reader for novelbin.com. Browse, search, download, and read chapters — all in the terminal.

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
- **Paste link** — open any novel by URL or slug
- **My Library** — browse locally downloaded novels, resume reading, delete
- **Reader** — next/prev (`n`/`p`), jump to chapter (`j`), download current (`d`)
- **Progress tracking** — auto-saves last chapter; ✓ marks read chapters
- **Download all** — batch download with progress bar
- **Translation** — Google Translate (12 languages); Arabic RTL layout
- **Delete with safety** — double-press `x` to confirm deletion

Key bindings in the reader:

| Key | Action |
|-----|--------|
| `n` / `p` | Next / Prev chapter |
| `j` | Jump to chapter number |
| `d` | Download current chapter |
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
pip install textual requests beautifulsoup4 deep-translator
python main.py
```

---

## How It Works

**Architecture:**
- `finder.py` — HTTP fetching, HTML parsing, chapter extraction, file saving
- `tui.py` — Textual TUI app: screens, widgets, navigation, translation, persistence
- `main.py` — Entry point (boots the TUI app)
- `novels/` — Downloaded chapters and JSON state (`progress.json`, `settings.json`)

---

## Roadmap

- [x] TUI mode (Textual interface)
- [x] Resume from last chapter (progress.json)
- [x] Search with auto-type and pagination
- [x] Translation (Google Translate, 12 languages, RTL support)
- [ ] Better text formatting (italics, line breaks, spacing)
- [ ] Search filters (genre, status, rating)
- [ ] Multi-source scraping (RoyalRoad, Webnovel, ScribbleHub)
- [ ] Offline reading mode
- [ ] Reading history across sessions

---

## Disclaimer

This tool scrapes publicly available content for personal use. Novels belong to their authors and translators. Support them if you can.
