import httpx
from .base import NewsProvider
from ._util import parse_dt, minutes_ago, read_estimate
from ..schemas import Article
from ..categories import param_for, classify
from ..config import settings

BASE = "https://newsapi.org/v2"


class NewsApiProvider(NewsProvider):
    """Adapter for https://newsapi.org

    Uses /top-headlines for scope=national (country param) and /everything for
    international / search. NewsAPI's category set is small, so we lean on the
    keyword classifier to map results onto our 9 channels.
    """

    name = "newsapi"
    live = True

    async def fetch(self, *, scope, category, q, page, page_size) -> list[Article]:
        key = settings.news_api_key
        params: dict = {"apiKey": key, "pageSize": min(page_size, 100), "page": page,
                        "language": settings.news_language}

        if scope == "national":
            # /everything has NO country filter — only /top-headlines does.
            endpoint = "/top-headlines"
            params["country"] = settings.news_country
            if q:
                params["q"] = q
        else:
            endpoint = "/everything"
            params["sortBy"] = "publishedAt"
            params["q"] = q or (category if category != "all" else "news")

        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.get(BASE + endpoint, params=params)
            r.raise_for_status()
            data = r.json()

        out: list[Article] = []
        for it in data.get("articles", []):
            title = it.get("title") or ""
            dek = it.get("description") or ""
            if not title:
                continue
            dt = parse_dt(it.get("publishedAt"))
            canon = classify(title, dek)
            out.append(Article(
                id=it.get("url") or title[:40],
                title=title, dek=dek, cat=canon,
                scope="national" if scope == "national" else "international",
                src=(it.get("source") or {}).get("name") or "Unknown",
                url=it.get("url"), image=it.get("urlToImage"),
                published_at=dt, min=minutes_ago(dt), read=read_estimate(dek),
            ))
        return out
