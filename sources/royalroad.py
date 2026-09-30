import urllib.parse

from bs4 import BeautifulSoup

from core.http_client import fetch_soup, get_client
from sources.base import Source


class RoyalRoadSource(Source):
    BASE_URL = "https://www.royalroad.com"

    def __init__(self):
        self._client = get_client()

    @property
    def name(self) -> str:
        return "royalroad"

    @property
    def label(self) -> str:
        return "RoyalRoad"

    @property
    def ascii_art(self) -> str:
        return """\
██████╗  ██████╗ ██╗   ██╗ █████╗ ██╗     ██████╗  ██████╗  █████╗ ██████╗
██╔══██╗██╔═══██╗╚██╗ ██╔╝██╔══██╗██║     ██╔══██╗██╔═══██╗██╔══██╗██╔══██╗
██████╔╝██║   ██║ ╚████╔╝ ███████║██║     ██████╔╝██║   ██║███████║██║  ██║
██╔══██╗██║   ██║  ╚██╔╝  ██╔══██║██║     ██╔══██╗██║   ██║██╔══██║██║  ██║
██║  ██║╚██████╔╝   ██║   ██║  ██║███████╗██║  ██║╚██████╔╝██║  ██║██████╔╝
╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝"""

    @property
    def browse_urls(self) -> dict[str, str]:
        return {
            "hot": "https://www.royalroad.com/fictions/best-rated",
            "latest": "https://www.royalroad.com/fictions/latest-updates",
            "popular": "https://www.royalroad.com/fictions/trending",
            "popular_this_week": "https://www.royalroad.com/fictions/popular-this-week",
            "newest": "https://www.royalroad.com/fictions/newest-fictions",
            "completed": "https://www.royalroad.com/fictions/complete",
            "rising_stars": "https://www.royalroad.com/fictions/rising-stars",
            "ongoing": "https://www.royalroad.com/fictions/ongoing",
        }

    @property
    def genres(self) -> dict[str, str]:
        return {
            "action-adventure": "Action",
            "adventure": "Adventure",
            "comedy": "Comedy",
            "drama": "Drama",
            "fantasy": "Fantasy",
            "horror": "Horror",
            "mystery": "Mystery",
            "romance": "Romance",
            "science-fiction": "Sci-Fi",
            "thriller": "Thriller",
            "wuxia": "Wuxia",
            "litrpg": "LitRPG",
            "gamelit": "GameLit",
        }

    async def fetch_url(self, url: str, params: dict | None = None) -> BeautifulSoup:
        return await fetch_soup(self._client, url, params=params)

    def parse_slug(self, url: str) -> str | None:
        o = urllib.parse.urlparse(url)
        if o.hostname and "royalroad.com" in o.hostname:
            parts = o.path.split("/")
            try:
                idx = parts.index("fiction")
            except ValueError:
                return None
            slug = "/".join(parts[idx + 1 :]).rstrip("/")
            return slug or None
        return None

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
            cover = img_tag.get("src", "") if img_tag else ""
            cover = self._absolutize(cover)
            results.append(
                {
                    "title": title_tag.text.strip(),
                    "author": "Unknown",
                    "slug": slug or "",
                    "latest": "",
                    "cover": cover,
                }
            )
        return results

    async def search(self, query: str, page: int = 1) -> tuple[list[dict], int]:
        soup = await self.fetch_url(
            "https://www.royalroad.com/fictions/search",
            params={"keyword": query, "page": page},
        )
        novels = self.extract_novel_rows(soup)
        page_links = soup.select("ul.pagination.justify-content-center a[data-page]")
        numbers = []
        for a in page_links:
            dp = a.get("data-page")
            if isinstance(dp, str) and dp.isdigit():
                numbers.append(int(dp))
        total_pages = max(numbers) if numbers else 1

        return novels, total_pages

    async def fetch_chapters(self, slug: str) -> list[dict]:
        url = f"https://www.royalroad.com/fiction/{slug}"
        soup = await self.fetch_url(url)
        rows = soup.select("table#chapters tr.chapter-row")
        chapters = []
        for i, row in enumerate(rows, 1):
            a = row.select_one("td a")
            if not a:
                continue
            href = a.get("href", "")
            chapters.append(
                {
                    "num": i,
                    "title": a.text.strip(),
                    "url": self._absolutize(str(href)),
                }
            )
        return chapters

    async def read_chapter(self, url: str) -> list[str] | None:
        soup = await self.fetch_url(url)
        main_content = soup.select_one(".chapter-content")
        if not main_content:
            return None
        return [p.get_text(strip=True) for p in main_content.find_all("p")]

    async def cover_url(self, slug: str) -> str:
        url = f"https://www.royalroad.com/fiction/{slug}"
        soup = await self.fetch_url(url)
        img = soup.find("img", class_="thumbnail")
        if img:
            return self._absolutize(str(img.get("src") or ""))
        return ""

    async def browse_genre(self, genre_slug: str) -> list[dict]:
        url = f"https://www.royalroad.com/fictions/search?tagsAdd={genre_slug}&globalFilters=true"
        soup = await self.fetch_url(url)
        return self.extract_novel_rows(soup)
