# Newsfold — full-stack newsletter

A filterable news/newsletter app. **React (Vite)** front end + **FastAPI** back end
with a provider-agnostic news layer. Runs end-to-end out of the box on built-in
sample data; drop in an API key to go live.

```
newsfold/
├── backend/                 FastAPI service
│   ├── app/
│   │   ├── main.py          routes: /api/news, /api/categories, /api/subscribe, /api/health
│   │   ├── config.py        env-driven settings
│   │   ├── categories.py    canonical channels + colors + per-provider category maps
│   │   ├── cache.py         in-memory TTL cache
│   │   ├── schemas.py       Pydantic models
│   │   ├── seed.py          sample dispatches
│   │   └── providers/       sample | newsapi | gnews | newsdata adapters
│   ├── requirements.txt
│   └── .env.example
└── frontend/                Vite + React
    └── src/{api.js, Newsfold.jsx, main.jsx}
```

## Run the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # works as-is on 'sample'
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the interactive API.

## Run the frontend

```bash
cd frontend
npm install
cp .env.example .env                                   # VITE_API_BASE=http://localhost:8000
npm run dev                                            # http://localhost:5173
```

The masthead shows a **Live feed** / **Sample feed** badge. If the backend is
down, the UI degrades to embedded sample data and shows a retry banner — it never
breaks.

## Going live (one config change)

Pick a provider, paste your key into `backend/.env`, restart uvicorn:

```env
NEWS_PROVIDER=newsdata      # sample | newsapi | gnews | newsdata
NEWS_API_KEY=your_key_here
NEWS_COUNTRY=us             # what "National" means (us, gb, in, ca, au, …)
```

Provider notes:
- **newsdata** (newsdata.io) — richest taxonomy, has native politics/environment categories. Recommended.
- **newsapi** (newsapi.org) — easy, but the free tier is dev-only (localhost) and has a small category set; the keyword classifier fills the gaps.
- **gnews** (gnews.io) — good free tier, topic-based.

To add another source, drop a new file in `app/providers/`, implement
`fetch(...) -> list[Article]`, and register it in `providers/__init__.py`.
Nothing else changes — the frontend only ever talks to `/api/news`.

> The sample dataset is illustrative, not live reporting.

## Newsletter digest (real emails)

The subscribe box persists subscribers (with their followed channels) to SQLite.
A scheduled trigger emails each subscriber a digest of their channels.

Set up email in `backend/.env` (Gmail example — create an App Password, not your login):
```
DIGEST_TOKEN=some-long-random-string
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-16-char-app-password
FROM_EMAIL=you@gmail.com
API_BASE_URL=https://your-backend.onrender.com   # for unsubscribe links
```

Trigger a send (what the scheduler calls):
```
curl -X POST https://your-backend.onrender.com/api/digest/run \
  -H "X-Digest-Token: some-long-random-string"
```
Preview an edition without sending:
```
curl "https://your-backend.onrender.com/api/digest/preview?email=you@x.com" \
  -H "X-Digest-Token: some-long-random-string"
```

**Scheduling (free):** the included `.github/workflows/digest.yml` pings `/api/digest/run`
daily. Add repo secrets `API_URL` and `DIGEST_TOKEN`. (Or use cron-job.org the same way.)

Digest only sends what's in the rolling store, so it needs the app to have fetched
live news recently. No SMTP config = digest logs and no-ops (safe).
