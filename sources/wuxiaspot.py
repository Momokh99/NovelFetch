from sources.base import Source
from typing import Optional
from bs4 import BeautifulSoup
import urllib.parse
import os
import httpx

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",}


class WuxiaSpotSource(Source):
    def __init__(self):
        self._client = httpx.AsyncClient(
            headers=headers,
            follow_redirects=True,
            timeout=30,
        )

    @property
    def name(self) -> str:
        return "wuxiaspot"

    @property
    def label(self) -> str:
        return "WuxiaSpot"
    @property
    def ascii_art(self) -> str:
        return """
    ██╗    ██╗██╗   ██╗██╗  ██╗██╗ █████╗    ███████╗██████╗  ██████╗ ████████╗
    ██║    ██║██║   ██║██║  ██║██║██╔══██╗   ██╔════╝██╔══██╗██╔═══██╗╚══██╔══╝
    ██║ █╗ ██║██║   ██║███████║██║███████║   ███████╗██████╔╝██║   ██║   ██║   
    ██║███╗██║██║   ██║██╔══██║██║██╔══██║   ╚════██║██╔═══╝ ██║   ██║   ██║   
    ╚███╔███╔╝╚██████╔╝██║  ██║██║██║  ██║██╗███████║██║     ╚██████╔╝   ██║   
     ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝╚══════╝╚═╝      ╚═════╝    ╚═╝"""
    @property
    def browse_urls(self) -> dict[str, str]:
        return {
            "hot": "https://www.wuxiaspot.com/list/all/all-onclick-0.html",
            "latest": "https://www.wuxiaspot.com/list/all/all-newstime-0.html",
            "popular": "https://www.wuxiaspot.com/list/all/all-onclick-0.html",
            "new": "https://www.wuxiaspot.com/list/all/all-newstime-0.html",
            "updates": "https://www.wuxiaspot.com/list/all/all-lastdotime-0.html",
            "ongoing": "https://www.wuxiaspot.com/list/all/Ongoing-onclick-0.html",
            "completed": "https://www.wuxiaspot.com/list/all/Completed-onclick-0.html",
        }

    @property
    def genres(self) -> dict[str, str]:
        return {
            "action": "Action",
            "adventure": "Adventure",
            "comedy": "Comedy",
            "drama": "Drama",
            "eastern": "Eastern",
            "ecchi": "Ecchi",
            "erciyuan": "Erciyuan",
            "fan-fiction": "Fan-Fiction",
            "fantasy": "Fantasy",
            "fantasy-romance": "Fantasy Romance",
            "game": "Game",
            "gender-bender": "Gender Bender",
            "girls-channel": "Girls Channel",
            "harem": "Harem",
            "historical": "Historical",
            "historical-romance": "Historical Romance",
            "horror": "Horror",
            "josei": "Josei",
            "magic": "Magic",
            "magical-realism": "Magical Realism",
            "martial-arts": "Martial Arts",
            "mecha": "Mecha",
            "military": "Military",
            "mystery": "Mystery",
            "other": "Other",
            "psychological": "Psychological",
            "romance": "Romance",
            "school-life": "School Life",
            "sci-fi": "Sci-Fi",
            "science-fiction": "Science Fiction",
            "seinen": "Seinen",
            "shoujo": "Shoujo",
            "shoujo-ai": "Shoujo Ai",
            "shounen": "Shounen",
            "shounen-ai": "Shounen Ai",
            "slice-of-life": "Slice Of Life",
            "smut": "Smut",
            "sports": "Sports",
            "supernatural": "Supernatural",
            "tragedy": "Tragedy",
            "two-dimensional": "Two-dimensional",
            "urban": "Urban",
            "urban-life": "Urban Life",
            "video-games": "Video Games",
            "virtual-reality": "Virtual Reality",
            "war": "War",
            "wuxia": "Wuxia",
            "xianxia": "Xianxia",
            "xuanhuan": "Xuanhuan",
            "yaoi": "Yaoi",
            "yuri": "Yuri",
        }

    async def fetch_url(self, url: str, params: Optional[dict] = None):
        response = await self._client.get(url, params=params)
        return BeautifulSoup(response.text, "html.parser")

    def parse_slug(self, url: str) -> Optional[str]:
        o = urllib.parse.urlparse(url)
        if o.hostname and "wuxiaspot.com" in o.hostname:
            path = o.path.rstrip(".html").rstrip("/")
            parts = path.split("/")
            if "novel" in parts:
                idx = parts.index("novel")
                return "/".join(parts[idx + 1:])


    def qualify_slug(self, slug: str) -> str:
        return f"wuxiaspot:{slug}"

    def extract_novel_rows(self, soup) -> list[dict]:
        results = []
        items = soup.select(".novel-item")
        for item in items:
            link = item.select_one("a[href*='/novel/']")
            if not link:
                continue
            href = link.get("href", "")
            slug = self.parse_slug("https://www.wuxiaspot.com" + href)
            title_el = item.select_one(".novel-title")
            title = title_el.text.strip() if title_el else ""
            img = item.select_one(".novel-cover img.lazy")
            cover = img.get("data-src", "") if img else ""
            results.append({
                "title": title,
                "author": "Unknown",
                "slug": slug or "",
                "latest": "",
                "cover": cover,
            })
        return results

    async def search(self, query: str, page: int = 1) -> tuple[list[dict], int]:
        url = "https://www.wuxiaspot.com/e/search/index.php"
        data = {
            "keyboard": query,
            "show": "title",
            "tempid": "1",
            "tbname": "news",
        }
        response = await self._client.post(url, data=data)
        soup = BeautifulSoup(response.text, "html.parser")
        novels = self.extract_novel_rows(soup)
        # Determine total pages from pagination
        page_links = soup.select(".pagination a")
        total_pages = 1
        for a in page_links:
            text = a.text.strip()
            if text.isdigit():
                num = int(text)
                if num > total_pages:
                    total_pages = num
        return novels, total_pages

    async def fetch_chapters(self, slug: str) -> list[dict]:
        url = f"https://www.wuxiaspot.com/novel/{slug}.html"
        soup = await self.fetch_url(url)
        chapters = []
        links = soup.select(".chapter-list li a")
        for i, a in enumerate(links, 1):
            href = a.get("href", "")
            title_el = a.select_one(".chapter-title")
            title = title_el.text.strip() if title_el else a.text.strip()
            if href and not href.startswith("http"):
                href = "https://www.wuxiaspot.com" + href
            chapters.append({
                "num": i,
                "title": title,
                "url": href,
            })
        return chapters


    async def read_chapter(self, url: str) -> Optional[list[str]]:
        soup = await self.fetch_url(url)
        content = soup.select_one(".chapter-content")
        if not content:
            return None
        return [p.get_text(strip=True) for p in content.find_all("p")]

    async def save_chapter(self, url: str, title: str, slug: str) -> bool:
        safe_title = title.replace("/", "-").replace(" ", "_")
        path = f"novels/{slug}/{safe_title}.txt"
        if os.path.exists(path):
            return False
        os.makedirs(os.path.dirname(path), exist_ok=True)
        content = await self.read_chapter(url)
        if not content:
            return False
        with open(path, "w", encoding="utf-8") as f:
            for p in content:
                f.write(p + "\n")
        return True

    async def cover_url(self, slug: str) -> str:
        url = f"https://www.wuxiaspot.com/novel/{slug}.html"
        soup = await self.fetch_url(url)
        img = soup.select_one(".cover img.lazy")
        if img:
            src = img.get("data-src") or img.get("src") or ""
            return str(src)
        return ""

    async def browse_genre(self, genre_slug: str) -> list[dict]:
        url = f"https://www.wuxiaspot.com/list/{genre_slug}/all-newstime-0.html"
        soup = await self.fetch_url(url)
        return self.extract_novel_rows(soup)






