import asyncio
import os

import ebooklib
from ebooklib import epub


def _chapter_sort_key(fname):
    import re
    nums = re.findall(r"\d+", fname)
    return int(nums[0]) if nums else 0

async def _export_epub(slug, source=None, chapters=None):
    chap_dir = os.path.join("novels", slug)
    raw_slug = slug.split(":", 1)[-1] if ":" in slug else slug
    title_parts = raw_slug.split("/", 1)
    title_stem = title_parts[-1] if len(title_parts) > 1 else title_parts[0]
    title = title_stem.replace("-", " ").title()

    book = epub.EpubBook()
    book.set_identifier(slug.replace("/", "-").replace(":", "-"))
    book.set_title(title)
    book.set_language("en")

    # Cover
    cover_data = None
    author = "Unknown"
    if source:
        try:
            url = await source.cover_url(raw_slug)
            if url:
                import httpx
                async with httpx.AsyncClient() as c:
                    r = await c.get(url)
                    if r.status_code == 200:
                        cover_data = r.content
        except Exception:
            pass
    book.add_author(author)

    # Chapters: either in-memory list or read from disk
    if chapters is not None:
        txt_list = list(chapters)
    else:
        if not os.path.isdir(chap_dir):
            return None
        txt_files = []
        for root, dirs, files in os.walk(chap_dir):
            for f in sorted(files):
                if f.endswith(".txt"):
                    rel = os.path.relpath(os.path.join(root, f), chap_dir)
                    txt_files.append(rel)
        txt_files.sort(key=_chapter_sort_key)
        txt_list = []
        for fname in txt_files:
            with open(os.path.join(chap_dir, fname), encoding="utf-8") as f:
                content = f.read()
            txt_list.append((fname, content))

    if not txt_list:
        return None

    epub_chapters = []
    for i, (fname, content) in enumerate(txt_list):
        ch_title = os.path.basename(fname).replace(".txt", "").replace("_", " ").title()
        paragraphs = content.split("\n\n")
        html = f"<h1>{ch_title}</h1>"
        for p in paragraphs:
            p = p.strip()
            if p:
                html += f"<p>{p}</p>"
        ch = epub.EpubHtml(title=ch_title, file_name=f"chap_{i+1:04d}.xhtml", lang="en")
        ch.content = html
        book.add_item(ch)
        epub_chapters.append(ch)

    book.toc = epub_chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    safe = title.replace(" ", "_").replace("/", "-")
    out = os.path.join(chap_dir, f"{safe}.epub")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    await asyncio.to_thread(epub.write_epub, out, book, {})
    return out


