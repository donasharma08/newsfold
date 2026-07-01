from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Category(BaseModel):
    key: str
    label: str
    color: str


class Article(BaseModel):
    id: str
    title: str
    dek: str = ""
    cat: str                       # canonical channel key
    scope: str                     # "national" | "international"
    src: str                       # source / publication name
    url: Optional[str] = None
    image: Optional[str] = None
    published_at: Optional[datetime] = None
    min: int = 0                   # minutes since publication (frontend shows "12m ago")
    read: int = 4                  # estimated read time in minutes


class NewsResponse(BaseModel):
    provider: str
    tier: str                      # "live" | "cached" | "sample"
    live: bool                     # True only when tier == "live"
    refreshed_at: Optional[datetime] = None   # last successful live pull
    count: int
    articles: list[Article]


class SubscribeIn(BaseModel):
    email: str
    channels: list[str] = []       # canonical channel keys the user follows
    scope: str = "all"             # national | international | all


class SubscribeOut(BaseModel):
    ok: bool
    message: str


class DigestResult(BaseModel):
    subscribers: int
    sent: int
