from abc import ABC, abstractmethod

from bs4 import BeautifulSoup


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
