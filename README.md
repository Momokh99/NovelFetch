# NovelFetch

A terminal-based novel reader for novelbin.com. Search, browse, and read chapters without ads, JavaScript, or distractions.

---

## What It Does

- Search by title or paste a link
- Browse by genre (10 supported), hot novels, latest releases, completions
- Read chapters with next/previous navigation
- Download chapters as .txt files

No ads. No popups. No bloat. Just text.

---

## Why Build This?

I read novels. A lot. And I got tired of browser tabs — slow loading, ads, popups, clutter. I just wanted the text.

So I built this. For fun. For myself.

What started as a 30-line script turned into 300+ lines across two files after too many nights debugging HTML selectors I didn't understand and `<template>` tags I had never seen before.

The hardest parts:
- **Dynamic HTML selectors** — every page type used slightly different classes. `.list.list-novel > .row` was the one selector that finally worked everywhere.
- **`<template>` tag parsing** — the chapter list hid inside a `<template>` tag. BeautifulSoup handled it strangely. `li[data-first-chapter-item]` was the fix after hours of trial and error.
- **Error handling** — users type "abc" instead of numbers. Networks fail mid-fetch. Chapters have no content. Every edge case had to be caught.

It was frustrating. It was also worth it. Now I read more because of it.

---

## Installation

```bash
git clone https://github.com/Momokh99/NovelFetch.git
cd NovelFetch
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install requests beautifulsoup4
python main.py
```

---

## How It Works

**Architecture:**
- `finder.py` — Fetches and parses HTML, extracts novels/chapters, downloads
- `main.py` — Terminal menu, user interaction, navigation flow

---

## Roadmap

- Resume from last chapter (save/load a JSON file)
- Better text formatting (italics, line breaks, spacing)
- Search filters (genre, status, rating)
- Proper CLI with argparse (command-based, no menus)
- Pagination for full chapter lists
- TUI mode (curses/Textual interface)
- Multi-source scraping (RoyalRoad, Webnovel, ScribbleHub)
- Translation support (Google Translate / LibreTranslate API)

---

## Disclaimer

This tool scrapes publicly available content for personal use. Novels belong to their authors and translators. Support them if you can.
