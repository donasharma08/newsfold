from .base import NewsProvider
from ..schemas import Article
from ..seed import SEED


class SampleProvider(NewsProvider):
    """Zero-config provider. Serves the seed dataset so the whole stack runs
    end-to-end with no API key. `live` is False so the UI shows a sample badge."""

    name = "sample"
    live = False

    async def fetch(self, *, scope, category, q, page, page_size) -> list[Article]:
        ql = q.strip().lower()
        out = []
        for a in SEED:
            if scope != "all" and a["scope"] != scope:
                continue
            if category != "all" and a["cat"] != category:
                continue
            if ql and ql not in f"{a['title']} {a['dek']} {a['src']}".lower():
                continue
            out.append(Article(**a))
        out.sort(key=lambda x: x.min)
        start = (page - 1) * page_size
        return out[start:start + page_size]
