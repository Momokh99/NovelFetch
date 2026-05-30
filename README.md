# NovelFetch

A terminal-based novel reader for novelbin.com. Search, browse, and read chapters without ads, JavaScript, or distractions.

## What It Does

- **Search** by title or paste a link
- **Browse** by genre (10+ supported), hot novels, latest releases, completions
- **Read** chapters with next/previous navigation
- **Download** chapters as .txt files

No ads. No popups. No bloat. Just text.

## Why Build This?

Novels need readers, not friction. Browser tabs are slow. Ads are loud. This runs in your terminal.

## Installation

```bash
git clone https://github.com/Momokh99/NovelFetch.git
cd NovelFetch
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install requests beautifulsoup4
python main.py
```

## How It Works

**Architecture:**
- `scraper.py` — Fetches and parses HTML from novelbin.com
- `parser.py` — Extracts chapters, metadata, and genres
- `cli.py` — Terminal UI and user interaction

**Key challenges solved:**
- Dynamic HTML selectors (`.list.list-novel > .row` works across all pages)
- `<template>` tag parsing for chapter lists (`li[data-first-chapter-item]`)
- Robust error handling for network failures and invalid input

## Roadmap

- [ ] Translation support (Google Translate/LibreTranslate)
- [ ] Multi-source scraping (RoyalRoad, Webnovel, ScribbleHub)
- [ ] Pagination for full chapter lists
- [ ] Resume from last chapter
- [ ] Search filters (genre, status, rating)
- [ ] Better text formatting (italics, line breaks)

## Disclaimer

This tool scrapes publicly available content for personal use. Novels belong to their authors and translators. Support them if you can.
