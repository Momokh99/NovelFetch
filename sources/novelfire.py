import asyncio
import urllib.parse

from bs4 import BeautifulSoup

from core.http_client import fetch_soup, get_client
from sources.base import Source, chapter_count_from_text


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
        # novelfire intermittently answers a chapter page with a JS
        # "Loading..." shell — HTTP 200 but no #content — when requests come
        # in bursts.  One retry clears it in practice; a genuinely missing
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
        """Every chapter lives at /book/<slug>/chapter-<N> with N == position."""
        if num < 1:
            return None
        return f"{self.BASE_URL}/book/{slug}/chapter-{num}"

    async def fetch_chapter_count(self, slug: str) -> int:
        """The book's own page prints the total ("2334 Chapters")."""
        url = f"https://novelfire.net/book/{slug}"
        for attempt in range(2):
            soup = await self.fetch_url(url)
            stated = chapter_count_from_text(soup.get_text(" ", strip=True))
            if stated:
                return stated
            if attempt == 0:
                # A JS "Loading..." shell states nothing, and read_chapter
                # already showed one retry clears it.  A book page that
                # genuinely lists no total costs this pause once per novel and
                # then falls back to a real fetch.
                await asyncio.sleep(1.5)
        return 0

    async def fetch_chapters(self, slug: str) -> list[dict]:
        chapters: list[dict] = []
        seen: set[str] = set()
        page = 1
        # The chapters page ships its own pagination bar (ul.pagination >
        # a.page-link) carrying the last page number, so the first response
        # already says how long this run will be.  ``None`` = no bar seen,
        # which falls back to walking pages until one comes back empty.
        first_page_rows = 0
        total_pages: int | None = None
        while True:
            soup = await self.fetch_url(
                f"https://novelfire.net/book/{slug}/chapters",
                params={"page": page},
            )
            rows = soup.select("ul.chapter-list li a[href]")
            if not rows:
                break
            if not first_page_rows:
                first_page_rows = len(rows)
                if soup.select_one("ul.pagination"):
                    total_pages = self.extract_total_pages(soup)
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
            # Stop before probing a page past the end.  Without a pagination
            # bar a short page is the last one; with one, the site's own page
            # count ends the run — but only when that page looks like an end
            # (short, or a novel that fits on one page), so a bar that
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
        soup = await self.fetch_url(f"https://novelfire.net/book/{slug}")
        img = soup.select_one('meta[property="og:image"]')
        return self._absolutize(str(img.get("content") or "")) if img else ""

    async def browse_genre(self, genre_slug: str) -> list[dict]:
        url = f"https://novelfire.net/genre-{genre_slug}/sort-new/status-all/all-novel"
        soup = await self.fetch_url(url)
        return self.extract_novel_rows(soup)
