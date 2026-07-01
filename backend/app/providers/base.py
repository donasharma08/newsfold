from abc import ABC, abstractmethod
from ..schemas import Article


class NewsProvider(ABC):
    """Adapter interface. Implement fetch() for any news source.

    A provider's only job is to talk to its API and return a list of
    normalised Article objects. All filtering semantics (scope, category, q)
    are passed in already canonicalised.
    """

    name: str = "base"
    live: bool = True

    @abstractmethod
    async def fetch(
        self,
        *,
        scope: str,        # "all" | "national" | "international"
        category: str,     # "all" | canonical channel key
        q: str,            # free-text search ("" = none)
        page: int,
        page_size: int,
    ) -> list[Article]:
        ...
