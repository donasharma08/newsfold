import httpx
from .base import NewsProvider
from ._util import parse_dt, minutes_ago, read_estimate
from ..schemas import Article
from ..categories import param_for, classify
from ..config import settings

BASE = "https://newsdata.io/api/1/news"


class NewsDataProvider(NewsProvider):
    """Adapter for https://newsdata.io (rich category set incl. politics/environment)."""

    name = "newsdata"
    live = True

    async def fetch(self, *, scope, category, q, page, page_size) -> list[Article]:
        params: dict = {"apikey": settings.news_api_key, "language": settings.news_language}
        if q:
            params["q"] = q
        if scope == "national":
            params["country"] = settings.news_country

        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.get(BASE, params=params)
            r.raise_for_status()
            data = r.json()

        out: list[Article] = []
        want = settings.news_country.lower()
        for it in data.get("results", []):
            title = it.get("title") or ""
            dek = it.get("description") or ""
            if not title:
                continue
            countries = [c.lower() for c in (it.get("country") or [])]
            # The country= query already filtered server-side. Only drop here
            # when NewsData explicitly tags a DIFFERENT country.
            if scope == "national" and countries and want not in countries:
                continue
            art_scope = "national" if (not countries or want in countries) else "international"
            dt = parse_dt(it.get("pubDate"))
            canon = classify(title, dek, fallback=it.get("category"))
            out.append(Article(
                id=it.get("link") or it.get("article_id") or title[:40],
                title=title, dek=dek, cat=canon,
                scope=art_scope,
                src=it.get("source_id") or "Unknown",
                url=it.get("link"), image=it.get("image_url"),
                published_at=dt, min=minutes_ago(dt), read=read_estimate(dek),
            ))
        return out[:page_size]
