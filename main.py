import urllib.parse

import finder

Banner = """
     ███╗   ██╗ ██████╗ ██╗   ██╗███████╗██╗     ██████╗ ██╗███╗   ██╗
     ████╗  ██║██╔═══██╗██║   ██║██╔════╝██║     ██╔══██╗██║████╗  ██║
     ██╔██╗ ██║██║   ██║██║   ██║█████╗  ██║     ██████╔╝██║██╔██╗ ██║
     ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══╝  ██║     ██╔══██╗██║██║╚██╗██║
     ██║ ╚████║╚██████╔╝ ╚████╔╝ ███████╗███████╗██████╔╝██║██║ ╚████║
     ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚══════╝╚══════╝╚═════╝ ╚═╝╚═╝  ╚═══╝
     ════════════════════════════════════════════════════════════════════
                          CLI Novel Reader v1
"""
menu = """
╔═══════════════════════════════════════════════╗
║  (1) Search by name                           ║
║  (2) Paste novel link                         ║
║  (3) Hot novels                               ║
║  (4) Latest releases                          ║
║  (5) Most popular                             ║
║  (6) Completed novels                         ║
║  (7) Browse by genre                          ║
║  (8) Download novel                           ║
║  (q) Quit                                     ║
╚═══════════════════════════════════════════════╝
"""
GENRES = {
    "action": "Action",
    "adventure": "Adventure",
    "comedy": "Comedy",
    "drama": "Drama",
    "fantasy": "Fantasy",
    "horror": "Horror",
    "mystery": "Mystery",
    "romance": "Romance",
    "sci-fi": "Sci-Fi",
    "thriller": "Thriller",
}
BROWSE_URLS = {
    "3": "https://novelbin.com/sort/top-hot-novel",
    "4": "https://novelbin.com/sort/latest",
    "5": "https://novelbin.com/sort/top-view-novel",
    "6": "https://novelbin.com/sort/completed",
}



def search_novel():
    keyword = input("\nSearch: ")
    encoded = urllib.parse.quote(keyword)
    url = f"https://novelbin.com/search?keyword={encoded}"
    soup = finder.fetch_url(url)
    novels = finder.extract_novel_rows(soup)
    if not novels:
        print("No novels found.")
        return
    novel = finder.pick_from_list(novels, "title")
    if novel is None:
        return
    browse_novel(novel["slug"])


def paste_link():
    url = input("Paste link: ").strip()
    if "/b/" not in url:
        print("Invalid link.")
        return
    slug = url.split("/b/")[-1].split("/")[0].split("?")[0]
    if slug:
        browse_novel(slug)
    else:
        print("Invalid link.")


def browse_list(key):
    url = BROWSE_URLS[key]
    soup = finder.fetch_url(url)
    novels = finder.extract_novel_rows(soup)
    if not novels:
        print("No novels found.")
        return
    novel = finder.pick_from_list(novels, "title")
    if novel is None:
        return
    browse_novel(novel["slug"])


def browse_genre():
    slugs = sorted(GENRES.keys())
    print("\nGenres:")
    for i, slug in enumerate(slugs, 1):
        print(f"{i:3}. {GENRES[slug]}")
    try:
        idx = int(input("\nPick number: ")) - 1
        if idx < 0 or idx >= len(slugs):
            print("Invalid.")
            return
    except ValueError:
        print("Invalid.")
        return
    url = f"https://novelbin.com/genre/{slugs[idx]}"
    print("Fetching...")
    soup = finder.fetch_url(url)
    results = finder.extract_novel_rows(soup)
    if not results:
        print("No results.")
        return
    print()
    novel = finder.pick_from_list(results, "title")
    if novel is None:
        return
    browse_novel(novel["slug"])


def browse_novel(slug):
    chapters = finder.fetch_chapters(slug)
    if not chapters:
        print("No chapters found.")
        return
    print(f"\nChapters (1-{len(chapters)}):")
    chapter = finder.pick_from_list(chapters, "title")
    if chapter is None:
        return
    from tui import NovelReader
    NovelReader(chapters, slug, start=chapter["num"] - 1).run()


def main():
    print(Banner)
    while True:
        print(menu)
        print("─" * 50)
        choice = input(">> ").strip()
        if choice == "q":
            print("Goodbye!")
            break
        elif choice == "1":
            search_novel()
        elif choice == "2":
            paste_link()
        elif choice in ("3", "4", "5", "6"):
            browse_list(choice)
        elif choice == "7":
            browse_genre()
        elif choice == "8":
            link = input("Paste novel link or slug: ").strip()
            if "/b/" in link:
                slug = link.split("/b/")[-1].split("/")[0]
            else:
                slug = link
            finder.download_novel(slug)
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
