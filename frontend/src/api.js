// Tiny API client for the Newsfold backend.
// Set VITE_API_BASE in .env to point at your FastAPI server.

const API_BASE =
  (typeof import.meta !== "undefined" &&
    import.meta.env &&
    import.meta.env.VITE_API_BASE) ||
  "http://localhost:8000";

async function jget(path, params) {
  const url = new URL(API_BASE + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v != null && v !== "" && v !== "all") url.searchParams.set(k, v);
    });
  }
  const res = await fetch(url.toString(), { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export const getCategories = () => jget("/api/categories");

export const getNews = ({ scope, category, q, page }) =>
  jget("/api/news", { scope, category, q, page });

export async function subscribe(email, channels = [], scope = "all") {
  const res = await fetch(API_BASE + "/api/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, channels, scope }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export { API_BASE };
