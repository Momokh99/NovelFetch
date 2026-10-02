import re
from abc import ABC, abstractmethod

from bs4 import BeautifulSoup


def chapter_count_from_text(text: str) -> int:
    """Parse an "N Chapters" figure out of a page's text; 0 when absent.

    A novel's own page states its length ("2334 Chapters"), which is what
    lets the chapter list be answered from one request instead of a download —
    see ``Source.fetch_chapter_count``.
    """
    match = re.search(r"(\d[\d,]*)\s+Chapters", text, re.IGNORECASE)
    return int(match.group(1).replace(",", "")) if match else 0


class Source(ABC):
    search_supported: bool = True
    BASE_URL: str = ""  # override in each concrete source

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def label(self) -> str: ...

    @property
    @abstractmethod
    def browse_urls(self) -> dict[str, str]: ...

    @abstractmethod
    def parse_slug(self, url: str) -> str | None: ...

    @abstractmethod
    def qualify_slug(self, slug: str) -> str: ...

    @abstractmethod
    async def fetch_url(
        self, url: str, params: dict | None = None
    ) -> BeautifulSoup: ...

    @abstractmethod
    async def search(self, query: str, page: int = 1) -> tuple[list[dict], int]: ...

    @abstractmethod
    async def fetch_chapters(self, slug: str) -> list[dict]: ...

    @abstractmethod
    async def read_chapter(self, url: str) -> list[str] | None: ...

    @abstractmethod
    async def cover_url(self, slug: str) -> str: ...

    @property
    @abstractmethod
    def genres(self) -> dict[str, str]: ...

    @property
    @abstractmethod
    def ascii_art(self) -> str: ...

    def _absolutize(self, url: str) -> str:
        """Prepend BASE_URL to a root-relative path; return absolute URLs unchanged."""
        if url.startswith("/"):
            return self.BASE_URL + url
        return url

    @abstractmethod
    async def browse_genre(self, genre_slug: str) -> list[dict]: ...

    def chapter_url(self, slug: str, num: int) -> str | None:
        """Chapter URL that can be built from the chapter number alone.

        Sources whose chapter pages follow a predictable pattern return one
        here, which lets :func:`core.utils._get_chapters` answer a request
        from a chapter count without downloading the table of contents.
        The default is ``None``: such sources always need a real fetch.
        """
        return None

    async def fetch_chapter_count(self, slug: str) -> int:
        """Exact chapter total for *slug*, or 0 when it costs a whole download.

        Asked only when nothing else knows how long the novel is, so a source
        that can print its total on one cheap page answers here instead of
        leaving the caller to page through its table of contents.  Returning 0
        means "unknown", which sends the caller back to a real fetch rather
        than to a chapter list built on a guess.
        """
        return 0
