import time
import json
import os
import urllib.parse

import requests
from bs4 import BeautifulSoup

if __name__ == "__main__":
    keyword = input("Search: ")
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://novelbin.com/search?keyword={encoded_keyword}"


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_url(url):
    response = requests.get(url, headers=headers)
    return BeautifulSoup(response.text, "html.parser")


def extract_novel_rows(soup):
    results = []
    rows = soup.select(".list.list-novel > .row")
    for row in rows:
        title_tag = row.select_one("h3.novel-title a")
        author_tag = row.select_one("span.author")
        chapter_tag = row.select_one("span.chr-text")
        if not title_tag:
            continue
        href = title_tag["href"]
        slug = href.split("/b/")[-1]
        results.append(
            {
                "title": title_tag.get("title") or title_tag.text.strip(),
                "author": author_tag.text.strip() if author_tag else "Unknown",
                "slug": slug,
                "latest": chapter_tag.text.strip() if chapter_tag else "",
            }
        )
    return results


def pick_from_list(items, label_key="title"):
    for i, item in enumerate(items, 1):
        print(f"{i}. {item[label_key]}")
    while True:
        try:
            choise = int(input("pick a number : ")) - 1
            if 0 <= choise < len(items):
                return items[choise]
        except ValueError:
            print("Invalid. Try again")


def fetch_chapters(slug):
    url = f"https://novelbin.com/b/{slug}"
    soup = fetch_url(url)
    items = soup.select("li[data-first-chapter-item] > a")
    chapters = []
    for i, a in enumerate(items, 1):
        chapters.append(
            {
                "num": i,
                "title": a.select_one(".nchr-text").text.strip(),
                "url": a["href"],
            }
        )
    return chapters


def read_chapter(url):
    """Prints the content of a chapter page."""
    soup = fetch_url(url)
    main_cont = soup.find("div", class_="chr-c")
    if not main_cont:
        print("Could not find chapter content.")
        return
    for p in main_cont.find_all("p"):
        print(p.text)


def save_chapter(url, title, slug):
    safe_title = title.replace("/", "-").replace(" ", "_")
    path = f"novels/{slug}/{safe_title}.txt"
    if os.path.exists(path):
        return False
    soup = fetch_url(url)
    main_cont = soup.find("div", class_="chr-c")
    if not main_cont:
        return False
    os.makedirs(f"novels/{slug}", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for p in main_cont.find_all("p"):
            f.write(p.text + "\n")
    return True


def download_novel(slug):
    chapters = fetch_chapters(slug)
    print(f"Downloading {len(chapters)} chapters to novels/{slug}/...")
    for chapter in chapters:
        if save_chapter(chapter["url"], chapter["title"], slug):
            print(f"  saved: {chapter['title']}")
        else:
            print(f"  skipped: {chapter['title']}")
        time.sleep(0.5)
