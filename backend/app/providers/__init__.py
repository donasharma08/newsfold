from .base import NewsProvider
from .sample import SampleProvider
from .newsapi import NewsApiProvider
from .gnews import GNewsProvider
from .newsdata import NewsDataProvider
from .currents import CurrentsProvider

_REGISTRY = {
    "sample": SampleProvider,
    "newsapi": NewsApiProvider,
    "gnews": GNewsProvider,
    "newsdata": NewsDataProvider,
    "currents": CurrentsProvider,
}


def get_provider(name: str) -> NewsProvider:
    cls = _REGISTRY.get(name, SampleProvider)
    return cls()


__all__ = ["NewsProvider", "get_provider"]
