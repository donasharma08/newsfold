import httpx
from .base import NewsProvider
from ._util import parse_dt, minutes_ago, read_estimate
from ..schemas import Article
from ..categories import param_for, classify
from ..config import settings

BASE = "https://api.currentsapi.services/v1"


class CurrentsProvider(NewsProvider):
    """Adapter for https://currentsapi.services

    /latest-news for headlines (supports country + category), /search for
    keyword queries. Response is {status, news:[{title, description, url,
    image, category:[...], published}]}.
    """

    name = "currents"
    live = True

    async def fetch(self, *, scope, category, q, page, page_size) -> list[Article]:
        params: dict = {
            "apiKey": settings.news_api_key,
            "language": settings.news_language,
            "page_size": min(page_size, 200),
        }
        if q:
            endpoint = "/search"
            params["keywords"] = q
        else:
            endpoint = "/latest-news"
        # We classify ourselves — never ask the API to filter by category.
        if scope == "national":
            params["country"] = settings.news_country.upper()   # Currents wants IN, not in

        # Currents' free tier 400s on country (and sometimes category) filtering.
        # Drop rejected params progressively so the feed stays LIVE.
        async with httpx.AsyncClient(timeout=12) as client:
            r = None
            for drop in (None, "country", "category"):
                if drop and drop in params:
                    params.pop(drop)
                r = await client.get(BASE + endpoint, params=params)
                if r.status_code != 400:
                    break
            r.raise_for_status()
            data = r.json()

        out: list[Article] = []
        for it in data.get("news", []):
            title = it.get("title") or ""
            dek = it.get("description") or ""
            if not title:
                continue
            dt = parse_dt(it.get("published"))
            canon = classify(title, dek, fallback=it.get("category"))
            out.append(Article(
                id=it.get("url") or it.get("id") or title[:40],
                title=title, dek=dek, cat=canon,
                scope="national" if scope == "national" else "international",
                src=(it.get("author") or "").strip() or "Currents",
                url=it.get("url"), image=it.get("image") if it.get("image") not in ("None", None) else None,
                published_at=dt, min=minutes_ago(dt), read=read_estimate(dek),
            ))
        return out
