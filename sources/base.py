from abc import ABC, abstractmethod
from typing import Optional


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
    def fetch_url(self, url: str, params: Optional[dict] = None):
        ...

    @abstractmethod
    def extract_novel_rows(self, soup) -> list[dict]:
        ...

    @abstractmethod
    def search(self, query: str, page: int = 1) -> tuple[list[dict], int]:
        ...

    @abstractmethod
    def fetch_chapters(self, slug: str) -> list[dict]:
        ...

    @abstractmethod
    def read_chapter(self, url: str) -> Optional[list[str]]:
        ...

    @abstractmethod
    def save_chapter(self, url: str, title: str, slug: str) -> bool:
        ...

    @abstractmethod
    def parse_slug(self, url: str) -> Optional[str]:
        ...

    @abstractmethod
    def qualify_slug(self, slug: str) -> str:
        ...

    @abstractmethod
    def cover_url(self, slug: str) -> str:
        ...

    @abstractmethod
    def browse_genre(self, genre_slug: str) -> list[dict]:
        ...
