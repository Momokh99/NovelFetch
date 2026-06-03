import sys
import termios
import tty
import urllib.parse

import finder


def getch(prompt=""):
    print(prompt, end="", flush=True)
    if not sys.stdin.isatty():
        return input().strip()
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    print(ch)
    return ch

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


def read_and_navigate(chapters, start_index):
    i = start_index
    while 0 <= i < len(chapters):
        print("=" * 60)
        print(f"  {chapters[i]['title']}")
        print("=" * 60)
        finder.read_chapter(chapters[i]["url"])
        answer = getch("(n)ext, (p)revious, (q)uit: ").lower()
        if answer == "n":
            i += 1
        elif answer == "p":
            i -= 1
        elif answer == "q":
            break


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
    read_and_navigate(chapters, chapter["num"] - 1)


def main():
    print(Banner)
    while True:
        print(menu)
        print("─" * 50)
        choice = getch(">> ")
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
