import asyncio
import urllib.parse

from bs4 import BeautifulSoup

from core.http_client import fetch_soup, get_client
from sources.base import Source


class NovelFireSource(Source):
    BASE_URL = "https://novelfire.net"
    # novelfire.net rate-limits bursty paging (HTTP 429).  Chapter lists live
    # behind ?page=, so a long novel is many back-to-back requests; this keeps
    # us under the server's threshold instead of relying on retries alone.
    PAGE_DELAY: float = 0.4

    def __init__(self):
        self._client = get_client()

    @property
    def name(self) -> str:
        return "novelfire"

    @property
    def label(self) -> str:
        return "NovelFire"

    @property
    def ascii_art(self) -> str:
        return """
    ███╗   ██╗ ██████╗ ██╗   ██╗███████╗██╗       ███████╗██╗██████╗ ███████╗
    ████╗  ██║██╔═══██╗██║   ██║██╔════╝██║       ██╔════╝██║██╔══██╗██╔════╝
    ██╔██╗ ██║██║   ██║██║   ██║█████╗  ██║       █████╗  ██║██████╔╝█████╗
    ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══╝  ██║       ██╔══╝  ██║██╔══██╗██╔══╝
    ██║ ╚████║╚██████╔╝ ╚████╔╝ ███████╗███████╗  ██║     ██║██║  ██║███████╗
    ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚══════╝╚══════╝  ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝"""

    @property
    def browse_urls(self) -> dict[str, str]:
        return {
            "home": "https://novelfire.net/home",
            "latest": "https://novelfire.net/genre-all/sort-new/status-all/all-novel",
            "popular": "https://novelfire.net/genre-all/sort-popular/status-all/all-novel",
            "newest": "https://novelfire.net/genre-all/sort-latest-release/status-all/all-novel",
            "completed": "https://novelfire.net/genre-all/sort-popular/status-completed/all-novel",
            "ongoing": "https://novelfire.net/genre-all/sort-popular/status-ongoing/all-novel",
            "chinese": "https://novelfire.net/genre-all/sort-popular/status-all/chinese-novel",
            "japanese": "https://novelfire.net/genre-all/sort-popular/status-all/japanese-novel",
            "english": "https://novelfire.net/genre-all/sort-popular/status-all/english-novel",
        }

    @property
    def genres(self) -> dict[str, str]:
        return {
            "all": "All",
            "action": "Action",
            "adventure": "Adventure",
            "anime": "Anime",
            "arts": "Arts",
            "comedy": "Comedy",
            "drama": "Drama",
            "eastern": "Eastern",
            "fan-fiction": "Fan-fiction",
            "fantasy": "Fantasy",
            "game": "Game",
            "historical": "Historical",
            "horror": "Horror",
            "isekai": "Isekai",
            "josei": "Josei",
            "magic": "Magic",
            "magical-realism": "Magical Realism",
            "martial-arts": "Martial Arts",
            "mecha": "Mecha",
            "military": "Military",
            "modern-life": "Modern Life",
            "movies": "Movies",
            "mystery": "Mystery",
            "other": "Other",
            "psychological": "Psychological",
            "realistic-fiction": "Realistic Fiction",
            "reincarnation": "Reincarnation",
            "romance": "Romance",
            "school-life": "School Life",
            "sci-fi": "Sci-fi",
            "seinen": "Seinen",
            "shoujo": "Shoujo",
            "shoujo-ai": "Shoujo Ai",
            "shounen": "Shounen",
            "shounen-ai": "Shounen Ai",
            "slice-of-life": "Slice of Life",
            "sports": "Sports",
            "supernatural": "Supernatural",
            "system": "System",
            "tragedy": "Tragedy",
            "urban": "Urban",
            "urban-life": "Urban Life",
            "video-games": "Video Games",
            "war": "War",
            "wuxia": "Wuxia",
            "xianxia": "Xianxia",
            "xuanhuan": "Xuanhuan",
        }

    def qualify_slug(self, slug: str) -> str:
        return f"novelfire:{slug}"

    def parse_slug(self, url: str) -> str | None:
        parsed = urllib.parse.urlparse(url)
        if parsed.hostname and parsed.hostname.removeprefix("www.") == "novelfire.net":
            path = parsed.path.strip("/")
            if path.startswith("book/"):
                slug = path[5:]
                if slug and "/" not in slug:
                    return slug
        return None

    async def fetch_url(self, url: str, params: dict | None = None) -> BeautifulSoup:
        return await fetch_soup(self._client, url, params=params)

    async def search(self, query: str, page: int = 1) -> tuple[list[dict], int]:
        soup = await self.fetch_url(
            "https://novelfire.net/search",
            params={"keyword": query, "type": "title", "page": page},
        )
        novels = self.extract_novel_rows(soup)
        total_pages = self.extract_total_pages(soup)
        return novels, total_pages

    def extract_total_pages(self, soup: BeautifulSoup) -> int:
        numbers = []
        for a in soup.select("ul.pagination a.page-link"):
            text = a.get_text(strip=True)
            if text.isdigit():
                numbers.append(int(text))
        return max(numbers) if numbers else 1

    async def read_chapter(self, url: str) -> list[str] | None:
        soup = await self.fetch_url(url)
        main_content = soup.find("div", id="content")
        if not main_content:
            return None
        return [p.get_text(strip=True) for p in main_content.find_all("p")]

    def extract_novel_rows(self, soup: BeautifulSoup) -> list[dict]:
        results = []
        for row in soup.select("li.novel-item"):
            a = row.select_one("a[href]")
            title = row.select_one("h4.novel-title")
            if not a or not title:
                continue
            slug = self.parse_slug(self._absolutize(str(a["href"])))
            cover = ""
            img = row.select_one("figure.novel-cover img")
            if img:
                raw = str(img.get("data-src") or img.get("src") or "")
                if not raw.startswith("data:"):
                    cover = self._absolutize(raw)
            results.append(
                {
                    "title": title.get_text(strip=True),
                    "author": "Unknown",
                    "slug": slug,
                    "latest": "",
                    "cover": cover,
                }
            )
        return results

    async def fetch_chapters(self, slug: str) -> list[dict]:
        chapters: list[dict] = []
        seen: set[str] = set()
        page = 1
        while True:
            soup = await self.fetch_url(
                f"https://novelfire.net/book/{slug}/chapters",
                params={"page": page},
            )
            rows = soup.select("ul.chapter-list li a[href]")
            if not rows:
                break
            for row in rows:
                href = str(row["href"])
                if href in seen:
                    # Malformed titles inject stray <a> tags; skip duplicates.
                    continue
                seen.add(href)
                num_el = row.select_one("span.chapter-no")
                title_el = row.select_one("strong.chapter-title")
                num_text = num_el.get_text(strip=True) if num_el else ""
                chapters.append(
                    {
                        "num": int(num_text)
                        if num_text.isdigit()
                        else len(chapters) + 1,
                        "title": title_el.get_text(strip=True)
                        if title_el
                        else row.get_text(strip=True),
                        "url": self._absolutize(href),
                    }
                )
            page += 1
            # Reaching here means this page had rows, so another request is
            # coming — wait before it.  The empty-page `break` above never
            # sleeps, so there is no trailing pause after the last page.
            await asyncio.sleep(self.PAGE_DELAY)
        return chapters

    async def cover_url(self, slug: str) -> str:
        soup = await self.fetch_url(f"https://novelfire.net/book/{slug}")
        img = soup.select_one('meta[property="og:image"]')
        return self._absolutize(str(img.get("content") or "")) if img else ""

    async def browse_genre(self, genre_slug: str) -> list[dict]:
        url = f"https://novelfire.net/genre-{genre_slug}/sort-new/status-all/all-novel"
        soup = await self.fetch_url(url)
        return self.extract_novel_rows(soup)
