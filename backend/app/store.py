"""Rolling news cache + subscribers, with two interchangeable backends.

  * DATABASE_URL set  -> PostgresStore  (Supabase / any Postgres: persistent)
  * otherwise         -> SqliteStore    (local file: zero-config dev)

Both expose the same methods, so the rest of the app never cares which is used.
On every successful live fetch we upsert articles (dedup by id/url) and prune
anything older than the retention window.
"""

import sqlite3
import threading
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from .schemas import Article
from .config import settings

log = logging.getLogger("newsfold.store")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_dt(v):
    """Normalise a stored value (datetime from PG, ISO str from SQLite) to UTC dt."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(v)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _row_to_article(r) -> Article:
    # r: id,title,dek,cat,scope,src,url,image,published_at,read,stored_at
    pub = _to_dt(r[8])
    base = pub or _to_dt(r[10]) or _now()
    mins = max(0, int((_now() - base).total_seconds() // 60))
    return Article(
        id=r[0], title=r[1], dek=r[2], cat=r[3], scope=r[4], src=r[5],
        url=r[6], image=r[7], published_at=pub, min=mins, read=r[9] or 4,
    )


# ----------------------------------------------------------------------------
class SqliteStore:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS articles(
                id TEXT PRIMARY KEY, title TEXT, dek TEXT, cat TEXT, scope TEXT,
                src TEXT, url TEXT, image TEXT, published_at TEXT, read INTEGER,
                stored_at TEXT)""")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_stored ON articles(stored_at)")
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS subscribers(
                email TEXT PRIMARY KEY, channels TEXT, scope TEXT, created_at TEXT)""")
        self.conn.commit()
        log.info("using SQLite store at %s", path)

    def save(self, articles: list[Article]) -> None:
        now = _now().isoformat()
        with self._lock:
            self.conn.executemany(
                "INSERT OR REPLACE INTO articles VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                [(a.id, a.title, a.dek, a.cat, a.scope, a.src, a.url, a.image,
                  a.published_at.isoformat() if a.published_at else None,
                  a.read, now) for a in articles])
            self.conn.commit()

    def prune(self, hours: int) -> None:
        cutoff = (_now() - timedelta(hours=hours)).isoformat()
        with self._lock:
            self.conn.execute("DELETE FROM articles WHERE stored_at < ?", (cutoff,))
            self.conn.commit()

    def last_refresh(self):
        with self._lock:
            row = self.conn.execute("SELECT MAX(stored_at) FROM articles").fetchone()
        return _to_dt(row[0]) if row and row[0] else None

    def recent(self, scope, category, q, hours, limit=60, offset=0) -> list[Article]:
        cutoff = (_now() - timedelta(hours=hours)).isoformat()
        sql = ("SELECT id,title,dek,cat,scope,src,url,image,published_at,read,stored_at "
               "FROM articles WHERE stored_at >= ?")
        p: list = [cutoff]
        if scope != "all":
            sql += " AND scope = ?"; p.append(scope)
        if category != "all":
            sql += " AND cat = ?"; p.append(category)
        if q:
            like = f"%{q.lower()}%"
            sql += " AND (lower(title) LIKE ? OR lower(dek) LIKE ? OR lower(src) LIKE ?)"
            p += [like, like, like]
        sql += " ORDER BY COALESCE(published_at, stored_at) DESC LIMIT ? OFFSET ?"
        p += [limit, offset]
        with self._lock:
            rows = self.conn.execute(sql, p).fetchall()
        return [_row_to_article(r) for r in rows]

    def add_subscriber(self, email, channels, scope) -> None:
        with self._lock:
            self.conn.execute("INSERT OR REPLACE INTO subscribers VALUES (?,?,?,?)",
                              (email, ",".join(channels), scope, _now().isoformat()))
            self.conn.commit()

    def remove_subscriber(self, email) -> int:
        with self._lock:
            cur = self.conn.execute("DELETE FROM subscribers WHERE email = ?", (email,))
            self.conn.commit()
            return cur.rowcount

    def list_subscribers(self) -> list[dict]:
        with self._lock:
            rows = self.conn.execute("SELECT email, channels, scope FROM subscribers").fetchall()
        return [{"email": r[0], "channels": [c for c in (r[1] or "").split(",") if c],
                 "scope": r[2] or "all"} for r in rows]


# ----------------------------------------------------------------------------
class PostgresStore:
    """Postgres backend (Supabase). Opens a short-lived connection per call so
    idle drops on the provider side never leave us with a dead socket."""

    def __init__(self, dsn: str):
        import psycopg  # imported lazily so SQLite-only dev needs no driver
        self.psycopg = psycopg
        if "sslmode=" not in dsn:
            dsn += ("&" if "?" in dsn else "?") + "sslmode=require"
        self.dsn = dsn
        with self._conn() as c, c.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS articles(
                id text PRIMARY KEY, title text, dek text, cat text, scope text,
                src text, url text, image text, published_at timestamptz,
                read int, stored_at timestamptz)""")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_stored ON articles(stored_at)")
            cur.execute("""CREATE TABLE IF NOT EXISTS subscribers(
                email text PRIMARY KEY, channels text, scope text, created_at timestamptz)""")
            c.commit()
        log.info("using Postgres store")

    def _conn(self):
        return self.psycopg.connect(self.dsn, connect_timeout=10)

    def save(self, articles: list[Article]) -> None:
        now = _now()
        rows = [(a.id, a.title, a.dek, a.cat, a.scope, a.src, a.url, a.image,
                 a.published_at, a.read, now) for a in articles]
        with self._conn() as c, c.cursor() as cur:
            cur.executemany(
                """INSERT INTO articles VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (id) DO UPDATE SET
                     title=EXCLUDED.title, dek=EXCLUDED.dek, cat=EXCLUDED.cat,
                     scope=EXCLUDED.scope, src=EXCLUDED.src, url=EXCLUDED.url,
                     image=EXCLUDED.image, published_at=EXCLUDED.published_at,
                     read=EXCLUDED.read, stored_at=EXCLUDED.stored_at""", rows)
            c.commit()

    def prune(self, hours: int) -> None:
        cutoff = _now() - timedelta(hours=hours)
        with self._conn() as c, c.cursor() as cur:
            cur.execute("DELETE FROM articles WHERE stored_at < %s", (cutoff,))
            c.commit()

    def last_refresh(self):
        with self._conn() as c, c.cursor() as cur:
            cur.execute("SELECT MAX(stored_at) FROM articles")
            row = cur.fetchone()
        return _to_dt(row[0]) if row and row[0] else None

    def recent(self, scope, category, q, hours, limit=60, offset=0) -> list[Article]:
        cutoff = _now() - timedelta(hours=hours)
        sql = ("SELECT id,title,dek,cat,scope,src,url,image,published_at,read,stored_at "
               "FROM articles WHERE stored_at >= %s")
        p: list = [cutoff]
        if scope != "all":
            sql += " AND scope = %s"; p.append(scope)
        if category != "all":
            sql += " AND cat = %s"; p.append(category)
        if q:
            like = f"%{q.lower()}%"
            sql += " AND (lower(title) LIKE %s OR lower(dek) LIKE %s OR lower(src) LIKE %s)"
            p += [like, like, like]
        sql += " ORDER BY COALESCE(published_at, stored_at) DESC LIMIT %s OFFSET %s"
        p += [limit, offset]
        with self._conn() as c, c.cursor() as cur:
            cur.execute(sql, p)
            rows = cur.fetchall()
        return [_row_to_article(r) for r in rows]

    def add_subscriber(self, email, channels, scope) -> None:
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                """INSERT INTO subscribers VALUES (%s,%s,%s,%s)
                   ON CONFLICT (email) DO UPDATE SET
                     channels=EXCLUDED.channels, scope=EXCLUDED.scope""",
                (email, ",".join(channels), scope, _now()))
            c.commit()

    def remove_subscriber(self, email) -> int:
        with self._conn() as c, c.cursor() as cur:
            cur.execute("DELETE FROM subscribers WHERE email = %s", (email,))
            n = cur.rowcount
            c.commit()
        return n

    def list_subscribers(self) -> list[dict]:
        def _txt(v):
            if isinstance(v, (bytes, bytearray, memoryview)):
                return bytes(v).decode("utf-8", "ignore")
            return v or ""
        with self._conn() as c, c.cursor() as cur:
            cur.execute("SELECT email, channels, scope FROM subscribers")
            rows = cur.fetchall()
        return [{"email": _txt(r[0]), "channels": [x for x in _txt(r[1]).split(",") if x],
                 "scope": _txt(r[2]) or "all"} for r in rows]


def get_store():
    if settings.database_url:
        return PostgresStore(settings.database_url)
    return SqliteStore(settings.db_path)
