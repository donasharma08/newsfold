# Deploy Newsfold

Backend → **Render** (free). Frontend → **Vercel** (free). Both pull from GitHub.

## 0. Push to GitHub
```bash
cd newsfold
git init && git add . && git commit -m "newsfold"
# create empty repo on github, then:
git remote add origin https://github.com/YOU/newsfold.git
git push -u origin main
```
`.env` is gitignored — secrets go in the host dashboards, not the repo.

## 1. Backend on Render
1. render.com → New → **Blueprint** → pick your repo. It reads `render.yaml`.
2. It creates `newsfold-api`. Fill the two secret env vars when asked:
   - `NEWS_API_KEY` = your provider key
   - `CORS_ORIGINS` = leave blank for now (set in step 3)
3. Deploy. You get a URL like `https://newsfold-api.onrender.com`.
4. Test: open `https://newsfold-api.onrender.com/api/health` → should show your provider + `live: true`.

(No blueprint? New → Web Service → repo → root dir `backend`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, add env vars manually.)

## 2. Frontend on Vercel
1. vercel.com → Add New → Project → pick your repo.
2. **Root Directory = `frontend`** (Framework auto-detects Vite).
3. Environment Variable:
   - `VITE_API_BASE` = `https://newsfold-api.onrender.com`
4. Deploy → URL like `https://newsfold.vercel.app`.

## 3. Open CORS back to the frontend
1. Render → newsfold-api → Environment → set
   `CORS_ORIGINS = https://newsfold.vercel.app`
2. Save → it redeploys.

Done. Visit the Vercel URL.

## Order matters
backend live (get URL) → frontend env points at it → backend CORS points back at frontend.

## Gotchas
- **Cold start:** Render free sleeps after ~15 min idle; first hit takes ~50s to wake. Fine for a portfolio.
- **Provider terms:** most free tiers (GNews, NewsData) are non-commercial / dev. OK for a public portfolio demo, not a real product.
- **Env changes need a redeploy** to take effect.

## Note on the rolling cache (SQLite)
The outage fallback stores recent news in a SQLite file (`RETENTION_HOURS`, default 6).
Render's **free** tier has an *ephemeral* disk — the file resets on every deploy/restart/cold-start.
That's fine: the cache simply rebuilds on the next successful live fetch. For a cache that
survives restarts, attach a Render Disk (paid) or point the store at your existing
Supabase/Postgres instead of SQLite.
