import re
import logging
from fastapi import FastAPI, Query, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .config import settings
from .cache import TTLCache
from .categories import CATEGORIES, CANON
from .schemas import Category, Article, NewsResponse, SubscribeIn, SubscribeOut, DigestResult
from .providers import get_provider
from .providers.sample import SampleProvider
from .store import get_store
from .digest import run_digest, build_preview, verify_unsub

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("newsfold")

app = FastAPI(title="Newsfold API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

cache = TTLCache(ttl=settings.cache_ttl)
provider = get_provider(settings.news_provider)
fallback = SampleProvider()
store = get_store()

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@app.get("/api/health")
async def health():
    return {"status": "ok", "provider": provider.name, "live": provider.live}


@app.get("/api/categories", response_model=list[Category])
async def categories():
    return CATEGORIES


@app.get("/api/news", response_model=NewsResponse)
async def news(
    scope: str = Query("all", pattern="^(all|national|international)$"),
    category: str = Query("all"),
    q: str = Query("", max_length=120),
    page: int = Query(1, ge=1, le=20),
    page_size: int = Query(30, ge=1, le=60),
):
    if category != "all" and category not in CANON:
        category = "all"

    cache_key = f"{provider.name}:{scope}:{category}:{q.strip().lower()}:{page}:{page_size}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    tier = "live"
    prov_name = provider.name
    offset = (page - 1) * page_size
    try:
        # Fetch broadly (no category to the API); we classify + filter ourselves.
        fresh = await provider.fetch(
            scope=scope, category="all", q=q, page=page, page_size=max(page_size, 60)
        )
        if not fresh and provider.name != "sample":
            raise ValueError("empty result from live provider")
        if provider.name != "sample":
            store.save(fresh)
            store.prune(settings.retention_hours)
            # Read back filtered by OUR classified category + scope, paginated.
            articles = store.recent(scope, category, q, settings.retention_hours,
                                    limit=page_size, offset=offset)
            if not articles and page == 1:
                articles = [a for a in fresh if category == "all" or a.cat == category][:page_size]
            tier = "live"
        else:
            tier = "sample"
            pool = [a for a in fresh if category == "all" or a.cat == category]
            articles = pool[offset:offset + page_size]
    except Exception as exc:  # noqa: BLE001 — degrade gracefully, never 500 the feed
        log.warning("provider '%s' failed (%s); trying cached store", provider.name, exc)
        # Tier 2: recent real news from SQLite/Postgres
        articles = store.recent(scope, category, q, settings.retention_hours,
                                limit=page_size, offset=offset)
        if articles:
            tier = "cached"
        else:
            # Tier 3: sample data floor — clearly badged, never mistaken for live.
            tier = "sample"
            prov_name = "sample"
            articles = await fallback.fetch(
                scope=scope, category=category, q=q, page=page, page_size=page_size
            )

    # Safety net: National must never contain non-national items.
    if scope == "national":
        articles = [a for a in articles if a.scope == "national"]

    resp = NewsResponse(
        provider=prov_name,
        tier=tier,
        live=(tier == "live"),
        refreshed_at=store.last_refresh(),
        count=len(articles),
        articles=articles,
    )
    # Only cache LIVE responses — fallback tiers must re-check the store / live
    # on every request so recovery is immediate.
    if tier == "live":
        await cache.set(cache_key, resp)
    return resp


@app.post("/api/subscribe", response_model=SubscribeOut)
async def subscribe(body: SubscribeIn):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        return SubscribeOut(ok=False, message="Enter a valid email address.")
    channels = [c for c in body.channels if c in CANON]
    scope = body.scope if body.scope in ("national", "international", "all") else "all"
    store.add_subscriber(email, channels, scope)
    log.info("subscriber saved: %s (%d channels)", email, len(channels))
    return SubscribeOut(ok=True, message="You're on the list — your first dispatch arrives tomorrow.")


@app.get("/api/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(email: str, t: str = ""):
    page = "<body style='font-family:Helvetica,Arial,sans-serif;text-align:center;padding:60px;color:#15151b;'>"
    if verify_unsub(email, t) and store.remove_subscriber(email.strip().lower()):
        return HTMLResponse(page + "<h2>Unsubscribed.</h2><p>You won't receive the Newsfold digest anymore.</p></body>")
    return HTMLResponse(page + "<h2>Invalid link.</h2><p>That unsubscribe link isn't valid.</p></body>", status_code=400)


@app.post("/api/digest/run", response_model=DigestResult)
async def digest_run(x_digest_token: str = Header(default="")):
    if not settings.digest_token or x_digest_token != settings.digest_token:
        raise HTTPException(status_code=401, detail="bad or missing digest token")
    result = run_digest(store)
    return DigestResult(**result)


@app.get("/api/digest/preview", response_class=HTMLResponse)
async def digest_preview(email: str, x_digest_token: str = Header(default="")):
    if not settings.digest_token or x_digest_token != settings.digest_token:
        raise HTTPException(status_code=401, detail="bad or missing digest token")
    return HTMLResponse(build_preview(store, email))
