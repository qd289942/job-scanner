from abc import ABC, abstractmethod
from typing import AsyncGenerator
from config import RawJobListing

from abc import ABC, abstractmethod
from typing import AsyncGenerator
from config import RawJobListing

class BaseScraper(ABC):
    def __init__(self, source_name: str):
        self.source_name = source_name

    @property
    def target_name(self) -> str:
        return (
            getattr(self, "company_name", None)
            or getattr(self, "search_keywords", None)
            or getattr(self, "search_term", None)
            or "all"
        )

    @abstractmethod
    async def scrape(self) -> AsyncGenerator[RawJobListing, None]:
        pass