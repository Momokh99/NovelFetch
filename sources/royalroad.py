from sources.base import Source
from typing import Optional
import requests
from bs4 import BeautifulSoup
import urllib.parse
import os

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
class RoyalRoadSource(Source):

    @property
    def name(self) -> str:
        return "royalroad"

    @property
    def label(self) -> str:
       return "RoyalRoad"

    @property
    def browse_urls(self) -> dict[str, str]:
        return {
            "best_rated": "https://www.royalroad.com/fictions/best-rated",
            "latest_updates": "https://www.royalroad.com/fictions/latest-updates",
            "trending": "https://www.royalroad.com/fictions/trending",
            "popular_this_week": "https://www.royalroad.com/fictions/popular-this-week",
            "newest": "https://www.royalroad.com/fictions/newest-fictions",
            "complete": "https://www.royalroad.com/fictions/complete",
            "rising_stars": "https://www.royalroad.com/fictions/rising-stars",
            "ongoing": "https://www.royalroad.com/fictions/ongoing",
        }

    def fetch_url(self, url: str, params: Optional[dict] = None):
        response = requests.get(url, headers=headers, params=params)
        return BeautifulSoup(response.text, "html.parser")

    def parse_slug(self, url: str) -> Optional[str]:
        o=urllib.parse.urlparse(url)
        if o.hostname and "royalroad.com" in o.hostname:
            p=o.path
            parts = p.split("/")
            idx = parts.index("fiction")
            slug_parts = parts[idx + 1:]
            slug = "/".join(slug_parts)
            slug = slug.rstrip("/")
            return slug


    def qualify_slug(self, slug: str) -> str:
        return f"royalroad:{slug}"

    def extract_novel_rows(self, soup) -> list[dict]:
        results = []
        rows = soup.select(".fiction-list-item.row")
        for row in rows:
            title_tag = row.select_one("h2.fiction-title a.font-red-sunglo.bold")
            if not title_tag:
                continue
            href = title_tag.get("href", "")
            slug = self.parse_slug("https://www.royalroad.com" + href)
            img_tag = row.select_one('img[data-type="cover"]')
            cover = img_tag["src"] if img_tag else ""
            results.append({
                "title": title_tag.text.strip(),
                "author": "Unknown",
                "slug": slug or "",
                "latest": "",
                "cover": cover,
            })
        return results

    def search(self, query: str, page: int = 1) -> tuple[list[dict], int]:
        url = f"https://www.royalroad.com/fictions/search?keyword={query}&page={page}"
        soup = self.fetch_url(url)
        novels = self.extract_novel_rows(soup)
        page_links = soup.select("ul.pagination.justify-content-center a[data-page]")
        numbers = []
        for a in page_links:
            dp = a.get("data-page")
            if dp and dp.isdigit():
                numbers.append(int(dp))
        total_pages = max(numbers) if numbers else 1

        return novels, total_pages


    def fetch_chapters(self, slug: str) -> list[dict]:
        url = f"https://www.royalroad.com/fiction/{slug}"
        soup = self.fetch_url(url)
        rows = soup.select("table#chapters tr.chapter-row")
        chapters = []
        for i, row in enumerate(rows, 1):
            a = row.select_one("td a")
            if not a:
                continue
            href = a.get("href", "")
            chapters.append({
                "num": i,
                "title": a.text.strip(),
                "url": "https://www.royalroad.com" + href,
            })
        return chapters

    def read_chapter(self, url: str) -> Optional[list[str]]:
        soup = self.fetch_url(url)
        main_cont = soup.select_one(".chapter-content")
        if not main_cont:
            return None
        return [p.get_text(strip=True) for p in main_cont.find_all("p")]

    def save_chapter(self, url: str, title: str, slug: str) -> bool:
        safe_title = title.replace("/", "-").replace(" ", "_")
        path = f"novels/{slug}/{safe_title}.txt"
        if os.path.exists(path):
            return False
        os.makedirs(os.path.dirname(path), exist_ok=True)
        content = self.read_chapter(url)
        if not content:
            return False
        with open(path, "w", encoding="utf-8") as f:
            for p in content:
                f.write(p + "\n")
        return True



    def cover_url(self, slug: str) -> str:
        url = f"https://www.royalroad.com/fiction/{slug}"
        soup = self.fetch_url(url)
        img = soup.find("img", class_="thumbnail")
        return img["src"] if img else ""

    def browse_genre(self, genre_slug: str) -> list[dict]:
        url = f"https://www.royalroad.com/fictions/genre/{genre_slug}"
        soup = self.fetch_url(url)
        return self.extract_novel_rows(soup)
