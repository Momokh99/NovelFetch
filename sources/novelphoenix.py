import asyncio
import re
import urllib.parse

from bs4 import BeautifulSoup

from core.http_client import fetch_soup, get_client
from sources.base import Source, chapter_count_from_text


class NovelPhoenixSource(Source):
    BASE_URL = "https://novelphoenix.com"
    # novelphoenix.com serves chapter lists 100 rows at a time, so a long
    # novel is many back-to-back requests.  It has not answered with 429 the
    # way novelfire.net does, but a short pause costs little next to the
    # request itself and keeps a large library open from looking like a burst.
    PAGE_DELAY: float = 0.25

    def __init__(self):
        self._client = get_client()

    @property
    def name(self) -> str:
        return "novelphoenix"

    @property
    def label(self) -> str:
        return "NovelPhoenix"

    @property
    def ascii_art(self) -> str:
        return """
    ███╗   ██╗  ██████╗  ██╗   ██╗ ███████╗ ██╗   ██████╗   ██╗  ██╗  ██████╗   ███████╗ ███╗   ██╗ ██╗  ██╗  ██╗
    █████╗  ██║ ██╔═══██╗ ╚██╗ ██╔╝ ██╔════╝ ██║   ██╔══██╗ ██║  ██║ ██╔═══██╗ ██╔════╝ █████╗  ██║ ██║  ╚██╗██╔╝
    ██╔██╗ ██║ ██║   ██║  ╚█████╔╝  █████╗   ██║   ██████╔╝ ██████╔╝ ██║   ██║ █████╗   ██╔██╗ ██║ ██║   ╚███╔╝
    ██║╚██╗██║ ██║   ██║   ╚██╔╝   ██╔══╝   ██║   ██╔═══╝  ██╔══██╗ ██║   ██║ ██╔══╝   ██║╚██╗██║ ██║   ██╔██╗
    ██║ ╚████║ ╚██████╔╝    ██║    ███████╗ ███████╗   ██║      ██║  ██║ ╚██████╔╝ ███████╗ ██║ ╚████║ ██║  ██╔╝ ██╗
    ╚═╝  ╚═══╝  ╚═════╝     ╚═╝    ╚══════╝ ╚══════╝   ╚═╝      ╚═╝  ╚═╝  ╚═════╝  ╚══════╝ ╚═╝  ╚═══╝ ██║  ╚═╝  ╚═╝"""

    @property
    def browse_urls(self) -> dict[str, str]:
        return {
            "hot": "https://novelphoenix.com/genre-all/sort-popular/status-all/all-novel",
            "latest": "https://novelphoenix.com/genre-all/sort-new/status-all/all-novel",
            "popular": "https://novelphoenix.com/genre-all/sort-popular/status-all/all-novel",
            "newest": "https://novelphoenix.com/genre-all/sort-latest-release/status-all/all-novel",
            "completed": "https://novelphoenix.com/genre-all/sort-popular/status-completed/all-novel",
            "ongoing": "https://novelphoenix.com/genre-all/sort-popular/status-ongoing/all-novel",
            "chinese": "https://novelphoenix.com/genre-all/sort-popular/status-all/chinese-novel",
            "japanese": "https://novelphoenix.com/genre-all/sort-popular/status-all/japanese-novel",
            "english": "https://novelphoenix.com/genre-all/sort-popular/status-all/english-novel",
        }

    @property
    def genres(self) -> dict[str, str]:
        # The site's own category list (id="categorylist"), minus the two
        # explicit-content genres the app does not surface.
        return {
            "all": "All",
            "action": "Action",
            "adventure": "Adventure",
            "anime": "Anime",
            "arts": "Arts",
            "comedy": "Comedy",
            "drama": "Drama",
            "eastern": "Eastern",
            "ecchi": "Ecchi",
            "fan-fiction": "Fan-fiction",
            "fantasy": "Fantasy",
            "game": "Game",
            "gender-bender": "Gender Bender",
            "harem": "Harem",
            "historical": "Historical",
            "horror": "Horror",
            "isekai": "Isekai",
            "josei": "Josei",
            "lgbt": "Lgbt+",
            "magic": "Magic",
            "magical-realism": "Magical realism",
            "manhua": "Manhua",
            "martial-arts": "Martial Arts",
            "mature": "Mature",
            "mecha": "Mecha",
            "military": "Military",
            "modern-life": "Modern life",
            "movies": "Movies",
            "mystery": "Mystery",
            "other": "Other",
            "psychological": "Psychological",
            "realistic-fiction": "Realistic fiction",
            "reincarnation": "Reincarnation",
            "romance": "Romance",
            "school-life": "School Life",
            "sci-fi": "Sci-fi",
            "seinen": "Seinen",
            "shoujo": "Shoujo",
            "shoujo-ai": "Shoujo ai",
            "shounen": "Shounen",
            "shounen-ai": "Shounen Ai",
            "slice-of-life": "Slice of Life",
            "sports": "Sports",
            "supernatural": "Supernatural",
            "system": "System",
            "tragedy": "Tragedy",
            "urban": "Urban",
            "urban-life": "Urban life",
            "video-games": "Video games",
            "war": "War",
            "wuxia": "Wuxia",
            "xianxia": "Xianxia",
            "xuanhuan": "Xuanhuan",
            "yaoi": "Yaoi",
            "yuri": "Yuri",
        }

    def qualify_slug(self, slug: str) -> str:
        return f"novelphoenix:{slug}"

    def parse_slug(self, url: str) -> str | None:
        parsed = urllib.parse.urlparse(url)
        if (
            parsed.hostname
            and parsed.hostname.removeprefix("www.") == "novelphoenix.com"
        ):
            path = parsed.path.strip("/")
            if path.startswith("novel/"):
                slug = path[6:]
                if slug and "/" not in slug:
                    return slug
        return None

    async def fetch_url(self, url: str, params: dict | None = None) -> BeautifulSoup:
        return await fetch_soup(self._client, url, params=params)

    async def search(self, query: str, page: int = 1) -> tuple[list[dict], int]:
        soup = await self.fetch_url(
            "https://novelphoenix.com/search",
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
        # Chapter text lives in #content.  A retry covers the occasional
        # truncated shell the site serves under load; a genuinely missing
        # chapter still falls through to None.
        for attempt in range(2):
            soup = await self.fetch_url(url)
            main_content = soup.find("div", id="content")
            if main_content:
                return [p.get_text(strip=True) for p in main_content.find_all("p")]
            if attempt == 0:
                await asyncio.sleep(1.5)
        return None

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

    def chapter_url(self, slug: str, num: int) -> str | None:
        """Every chapter lives at /novel/<slug>/chapter-<N> with N == position."""
        if num < 1:
            return None
        return f"{self.BASE_URL}/novel/{slug}/chapter-{num}"

    async def fetch_chapter_count(self, slug: str) -> int:
        """The novel's own page prints the total in div.header-stats ("695 Chapters")."""
        url = f"{self.BASE_URL}/novel/{slug}"
        for attempt in range(2):
            soup = await self.fetch_url(url)
            stats = soup.select_one("div.header-stats")
            text = (
                stats.get_text(" ", strip=True)
                if stats
                else soup.get_text(" ", strip=True)
            )
            stated = chapter_count_from_text(text)
            if stated:
                return stated
            if attempt == 0:
                await asyncio.sleep(1.5)
        return 0

    def extract_chapter_pages(self, soup: BeautifulSoup) -> int:
        """Last chapter-range page, read off the pager's <select> option URLs.

        The chapter list paginates by chapter ranges (100 rows per page), not
        with the numbered ul.pagination bar the listing pages use, so the
        select options carry the authoritative page count.
        """
        pages = []
        for opt in soup.select('select[aria-label="Chapter range"] option[value]'):
            match = re.search(r"[?&]page=(\d+)", str(opt["value"]))
            if match:
                pages.append(int(match.group(1)))
        return max(pages) if pages else 1

    async def fetch_chapters(self, slug: str) -> list[dict]:
        chapters: list[dict] = []
        seen: set[str] = set()
        page = 1
        first_page_rows = 0
        total_pages: int | None = None
        while True:
            soup = await self.fetch_url(
                f"{self.BASE_URL}/novel/{slug}/chapters",
                params={"page": page},
            )
            rows = soup.select("ul.chapter-list li a[href]")
            if not rows:
                break
            if not first_page_rows:
                first_page_rows = len(rows)
                if soup.select_one('select[aria-label="Chapter range"]'):
                    total_pages = self.extract_chapter_pages(soup)
            for row in rows:
                href = str(row["href"])
                if href in seen:
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
            # Stop before probing a page past the end.  Without the range
            # select a short page is the last one; with one, the site's own
            # page count ends the run — but only when that page looks like an
            # end (short, or a novel that fits on one page), so a select that
            # under-reports the count can never silently drop chapters.
            if total_pages is None:
                if len(rows) < first_page_rows:
                    break
            elif page >= total_pages and (
                total_pages <= 1 or len(rows) < first_page_rows
            ):
                break
            page += 1
            # Every `break` above lands before this line, so a run never
            # sleeps after the page it knows is the last one.
            await asyncio.sleep(self.PAGE_DELAY)
        return chapters

    async def cover_url(self, slug: str) -> str:
        soup = await self.fetch_url(f"{self.BASE_URL}/novel/{slug}")
        img = soup.select_one('meta[property="og:image"]')
        return self._absolutize(str(img.get("content") or "")) if img else ""

    async def browse_genre(self, genre_slug: str) -> list[dict]:
        url = f"{self.BASE_URL}/genre-{genre_slug}/sort-new/status-all/all-novel"
        soup = await self.fetch_url(url)
        return self.extract_novel_rows(soup)
