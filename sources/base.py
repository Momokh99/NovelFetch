from abc import ABC, abstractmethod
from typing import Any, Optional


class Source(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def label(self) -> str:
        ...

    @property
    @abstractmethod
    def browse_urls(self) -> dict[str, str]:
        ...

    @abstractmethod
    async def fetch_url(self, url: str, params: Optional[dict] = None) -> Any: ...

    @abstractmethod
    async def search(self, query: str, page: int = 1) -> tuple[list[dict], int]: ...

    @abstractmethod
    async def fetch_chapters(self, slug: str) -> list[dict]: ...

    @abstractmethod
    async def read_chapter(self, url: str) -> Optional[list[str]]: ...

    @abstractmethod
    async def save_chapter(self, url: str, title: str, slug: str) -> bool: ...

    @abstractmethod
    async def cover_url(self, slug: str) -> str: ...

    @property
    @abstractmethod
    def genres(self) -> dict[str, str]:
        ...

    @abstractmethod
    async def browse_genre(self, genre_slug: str) -> list[dict]: ...
