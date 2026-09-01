# Domain Context: NovelFetch

> This file is the shared vocabulary and decision record for the NovelFetch codebase.
> It is written incrementally by the `/domain-modeling` skill when terms or decisions
> actually get resolved — do not treat it as complete.

## What this is

NovelFetch is a novel reader with a pluggable source system: browse, search, download,
and read chapters. The app ships two frontends sharing one framework: a terminal
(Textual) TUI and a KivyMD GUI (desktop + Android).

## Vocabulary

Terms in use, to keep skills' output consistent with how the project actually talks:

- **novel** — a work on the shelf; identified by a slug.
- **source** — a pluggable scraper/registry entry that serves novels and chapters.
- **library** — locally tracked/downloaded novels, browsable and resumable.
- **chapter** — an individual installment of a novel.
- **progress** — the last-read position per novel; powers read/unread and resume.
- **tracked** — a novel marked to monitor for updates/downloads.
- **translation** — transforming chapter text to another language (Google Translate, 12 languages; Arabic RTL).
- **EPUB export** — generating EPUB files from downloaded chapters for offline reading on e-readers.
- **TUI app** — the terminal (Textual) frontend; lives in `tui/`.
- **GUI app** — the KivyMD frontend, desktop and Android; lives in `gui/`.
- **core** — the framework shared by both frontends (progress, translation, EPUB, source dispatch); lives in `core/`.

## Decisions

Recorded under [`docs/adr/`](docs/adr/README.md). Add an ADR when a meaningful,
non-obvious decision is made rather than burying it in prose here.
