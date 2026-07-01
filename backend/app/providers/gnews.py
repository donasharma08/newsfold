import httpx
from .base import NewsProvider
from ._util import parse_dt, minutes_ago, read_estimate
from ..schemas import Article
from ..categories import param_for, classify
from ..config import settings

BASE = "https://gnews.io/api/v4"


class GNewsProvider(NewsProvider):
    """Adapter for https://gnews.io"""

    name = "gnews"
    live = True

    async def fetch(self, *, scope, category, q, page, page_size) -> list[Article]:
        params: dict = {"apikey": settings.news_api_key, "lang": settings.news_language,
                        "max": min(page_size, 25), "page": page}

        if q:
            endpoint = "/search"
            params["q"] = q
        else:
            endpoint = "/top-headlines"
        if scope == "national":
            params["country"] = settings.news_country

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
                url=it.get("url"), image=it.get("image"),
                published_at=dt, min=minutes_ago(dt), read=read_estimate(dek),
            ))
        return out
