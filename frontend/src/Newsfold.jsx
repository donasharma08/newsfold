import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import {
  Sun, Moon, Search, Plus, Check, Bookmark, Clock,
  ArrowUpRight, Mail, X, Globe, MapPin, Inbox, Wifi, WifiOff, RefreshCw, History,
} from "lucide-react";
import { getNews, getCategories, subscribe } from "./api";

/* ---------- categories fallback (if /api/categories is unreachable) ---------- */
const FALLBACK_CATEGORIES = [
  { key: "politics", label: "Politics", color: "#D6453D" },
  { key: "economy", label: "Economy", color: "#1FA47A" },
  { key: "society", label: "Society", color: "#7C5CFC" },
  { key: "culture", label: "Culture", color: "#E0A82E" },
  { key: "technology", label: "Technology", color: "#2D6FF0" },
  { key: "environment", label: "Environment", color: "#3DA35D" },
  { key: "health", label: "Health", color: "#E2557B" },
  { key: "science", label: "Science", color: "#16A8B8" },
  { key: "sports", label: "Sports", color: "#F2792E" },
];

/* ---------- localStorage persistence (safe in incognito/blocked) ---------- */
const LS = {
  get(k, fb) {
    try { const v = localStorage.getItem(k); return v == null ? fb : JSON.parse(v); }
    catch { return fb; }
  },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } },
};

/* ---------- helpers ---------- */
function timeAgo(min) {
  if (min < 60) return `${min}m ago`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}
function todayLine() {
  try {
    return new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  } catch { return "Today"; }
}
function ago(iso) {
  if (!iso) return null;
  const mins = Math.max(0, (Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${Math.round(mins)} min ago`;
  const hrs = mins / 60;
  if (hrs < 24) return `${Math.round(hrs)} hr ago`;
  return `${Math.round(hrs / 24)} d ago`;
}

/* ---------- sample data (the floor shown when live + cached are empty) ---------- */
const SEED = [
  { id: "s1", cat: "politics", scope: "national", src: "Capital Ledger", min: 14, read: 6, title: "Parliament passes revised data-protection bill after marathon session", dek: "The amended framework tightens consent rules and creates an independent oversight board, though enforcement timelines remain contested." },
  { id: "s2", cat: "economy", scope: "international", src: "Globe Wire", min: 41, read: 5, title: "Central banks signal a slower path on rate cuts as inflation cools unevenly", dek: "Policymakers across three continents struck a cautious tone, wary that easing too quickly could reignite price pressures." },
  { id: "s3", cat: "technology", scope: "international", src: "Frontier Desk", min: 58, read: 4, title: "Open-source models close the gap with proprietary systems on key benchmarks", dek: "A new wave of community-trained models is shifting how startups think about cost, control, and deployment." },
  { id: "s4", cat: "society", scope: "national", src: "Civic Daily", min: 95, read: 7, title: "Cities pilot four-day work weeks, and early data looks surprisingly good", dek: "Productivity held steady while reported burnout dropped sharply across the trial cohorts." },
  { id: "s5", cat: "culture", scope: "national", src: "The Meridian", min: 130, read: 5, title: "Independent bookshops report their strongest year in over a decade", dek: "Curated shelves and community events are pulling readers back from the algorithmic feed." },
  { id: "s6", cat: "environment", scope: "international", src: "Atlas Report", min: 165, read: 8, title: "Record investment in grid-scale storage reshapes the renewables math", dek: "Falling battery costs are making round-the-clock clean power viable in regions that once relied on gas." },
  { id: "s7", cat: "health", scope: "national", src: "Harbor Review", min: 190, read: 6, title: "Public clinics expand mental-health screening into routine checkups", dek: "Early-detection programs aim to catch conditions before they escalate, but staffing remains the bottleneck." },
  { id: "s8", cat: "science", scope: "international", src: "Northline", min: 220, read: 9, title: "Astronomers map a faint galaxy that predates most known structures", dek: "The find pushes back the timeline for early galaxy formation and raises fresh questions for cosmologists." },
  { id: "s9", cat: "economy", scope: "national", src: "The Standard", min: 260, read: 4, title: "Small-business lending rebounds as regional banks loosen terms", dek: "Owners cite easier access to working capital, though many remain cautious about expansion." },
  { id: "s10", cat: "sports", scope: "international", src: "Continental Post", min: 300, read: 3, title: "Underdog squad stuns the title favorites in a late-game collapse", dek: "A disciplined defensive game plan undid a side that had not lost at home all season." },
  { id: "s11", cat: "technology", scope: "national", src: "Frontier Desk", min: 340, read: 5, title: "Regulators draft first rules for autonomous delivery on city streets", dek: "The proposal balances safety testing with a path for operators to scale pilots responsibly." },
  { id: "s12", cat: "politics", scope: "international", src: "Globe Wire", min: 380, read: 6, title: "Regional bloc reaches a tentative deal on migration and border funding", dek: "Negotiators called it a fragile compromise that still needs ratification from member states." },
  { id: "s13", cat: "society", scope: "national", src: "Civic Daily", min: 420, read: 5, title: "Volunteer networks step in as housing pressure reshapes mid-size towns", dek: "Mutual-aid groups are filling gaps that strained municipal services can no longer cover alone." },
  { id: "s14", cat: "health", scope: "international", src: "Northline", min: 500, read: 8, title: "A long-running study links sleep regularity to long-term heart health", dek: "Consistency of sleep timing mattered as much as total hours, researchers found." },
];
function filterSeed({ scope, category, q }) {
  const ql = (q || "").trim().toLowerCase();
  return SEED.filter((a) => {
    if (scope !== "all" && a.scope !== scope) return false;
    if (category !== "all" && a.cat !== category) return false;
    if (ql && !`${a.title} ${a.dek} ${a.src}`.toLowerCase().includes(ql)) return false;
    return true;
  });
}

const STYLES = `
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,500;12..96,600;12..96,700;12..96,800&display=swap');
.nf-root { --bg:#F5F4F0; --surface:#FFFFFF; --surface-2:#FBFAF7; --ink:#15151B; --muted:#5C5C68; --faint:#8A8A95; --line:#E6E4DE; --accent:#8B2332; --accent-soft:#F4E4E6; --accent-ink:#FFFFFF; --shadow:rgba(20,20,26,.08); }
.nf-root.dark { --bg:#0E0E13; --surface:#16161D; --surface-2:#1C1C25; --ink:#F3F2EE; --muted:#A4A4B0; --faint:#71717C; --line:#2A2A33; --accent:#FF6B7A; --accent-soft:#2A1A1E; --accent-ink:#15151B; --shadow:rgba(0,0,0,.45); }
.nf-root { background:var(--bg); color:var(--ink); font-family:'Bricolage Grotesque',system-ui,sans-serif; min-height:100vh; transition:background .35s ease,color .35s ease; -webkit-font-smoothing:antialiased; }
.nf-root *{box-sizing:border-box;}
.nf-wrap{ max-width:1120px; margin:0 auto; padding:0 20px; }
.nf-mast{ position:sticky; top:0; z-index:30; background:var(--bg); border-bottom:1px solid var(--line); transition:background .35s ease,border-color .35s ease; }
.nf-mast-top{ display:flex; align-items:center; justify-content:space-between; gap:16px; padding:18px 0 14px; }
.nf-brand{ display:flex; align-items:baseline; gap:10px; }
.nf-mark{ width:11px; height:11px; border-radius:50%; background:var(--accent); display:inline-block; transform:translateY(-1px); }
.nf-word{ font-family:'Bricolage Grotesque',sans-serif; font-weight:700; font-size:27px; letter-spacing:-.8px; line-height:1; }
.nf-word b{ color:var(--accent); font-weight:600; }
.nf-tools{ display:flex; align-items:center; gap:10px; }
.nf-search{ display:flex; align-items:center; gap:8px; background:var(--surface); border:1px solid var(--line); border-radius:999px; padding:8px 14px; min-width:180px; transition:border-color .2s ease; }
.nf-search:focus-within{ border-color:var(--accent); }
.nf-search input{ border:0; outline:0; background:transparent; color:var(--ink); font-size:14px; width:100%; font-family:inherit; }
.nf-search input::placeholder{ color:var(--faint); }
.nf-icon-btn{ display:inline-flex; align-items:center; justify-content:center; width:42px; height:42px; border-radius:999px; border:1px solid var(--line); background:var(--surface); color:var(--ink); cursor:pointer; transition:background .2s ease,border-color .2s ease,color .2s ease; flex:0 0 auto; }
.nf-icon-btn:hover{ border-color:var(--accent); color:var(--accent); }
.nf-kicker{ font-family:'Bricolage Grotesque',sans-serif; font-size:12px; letter-spacing:.4px; color:var(--muted); padding-bottom:14px; display:flex; flex-wrap:wrap; align-items:center; gap:6px 14px; }
.nf-kicker .dot{ color:var(--faint); }
.nf-kicker b{ color:var(--accent); font-weight:700; }
.nf-status{ display:inline-flex; align-items:center; gap:5px; padding:3px 10px; border-radius:999px; font-size:11px; font-weight:700; letter-spacing:.3px; }
.nf-status.live{ background:var(--accent-soft); color:var(--accent); }
.nf-status.cached{ background:var(--surface); border:1px solid var(--line); color:#B8860B; }
.nf-status.sample{ background:var(--surface); border:1px solid var(--line); color:var(--faint); }
.nf-controls{ display:flex; align-items:center; gap:14px; flex-wrap:wrap; padding:20px 0 14px; }
.nf-seg{ display:inline-flex; background:var(--surface); border:1px solid var(--line); border-radius:999px; padding:3px; }
.nf-seg button{ border:0; background:transparent; color:var(--muted); font-family:inherit; font-size:13px; font-weight:600; padding:8px 15px; border-radius:999px; cursor:pointer; display:inline-flex; align-items:center; gap:6px; transition:color .2s ease,background .2s ease; }
.nf-seg button[aria-pressed="true"]{ background:var(--ink); color:var(--bg); }
.nf-spacer{ flex:1 1 auto; }
.nf-toggle{ display:inline-flex; align-items:center; gap:8px; border:1px solid var(--line); background:var(--surface); color:var(--ink); border-radius:999px; padding:8px 14px; font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; transition:border-color .2s ease,background .2s ease,color .2s ease; }
.nf-toggle[aria-pressed="true"]{ background:var(--accent); border-color:var(--accent); color:var(--accent-ink); }
.nf-chips{ display:flex; gap:9px; overflow-x:auto; padding:6px 0 18px; scrollbar-width:none; }
.nf-chips::-webkit-scrollbar{ display:none; }
.nf-chip{ display:inline-flex; align-items:center; gap:9px; background:var(--surface); border:1px solid var(--line); border-radius:999px; padding:7px 7px 7px 13px; flex:0 0 auto; transition:border-color .2s ease,background .2s ease; }
.nf-chip[data-active="true"]{ border-color:var(--ink); }
.nf-chip .pick{ display:inline-flex; align-items:center; gap:8px; border:0; background:transparent; color:var(--ink); font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; }
.nf-chip .swatch{ width:9px; height:9px; border-radius:50%; flex:0 0 auto; }
.nf-follow{ display:inline-flex; align-items:center; justify-content:center; gap:5px; border:1px solid var(--line); border-radius:999px; height:28px; padding:0 11px; font-family:inherit; font-size:12px; font-weight:700; cursor:pointer; background:var(--surface-2); color:var(--muted); transition:all .18s ease; }
.nf-follow:hover{ color:var(--ink); border-color:var(--ink); }
.nf-follow[data-on="true"]{ background:var(--accent); border-color:var(--accent); color:var(--accent-ink); }
.nf-chip-all{ display:inline-flex; align-items:center; border:1px solid var(--line); background:var(--surface); color:var(--ink); border-radius:999px; padding:8px 15px; font-family:inherit; font-size:13px; font-weight:600; cursor:pointer; flex:0 0 auto; transition:border-color .2s ease; }
.nf-chip-all[data-active="true"]{ border-color:var(--ink); background:var(--ink); color:var(--bg); }
.nf-seclabel{ font-family:'Bricolage Grotesque',sans-serif; font-size:12px; letter-spacing:1.5px; text-transform:uppercase; color:var(--faint); display:flex; align-items:center; gap:10px; margin:26px 0 14px; }
.nf-seclabel::after{ content:""; flex:1; height:1px; background:var(--line); }
.nf-banner{ display:flex; align-items:center; gap:12px; background:var(--surface); border:1px solid var(--line); border-left:4px solid var(--accent); border-radius:12px; padding:13px 16px; font-size:13.5px; color:var(--muted); margin-bottom:6px; }
.nf-banner b{ color:var(--ink); }
.nf-banner button{ margin-left:auto; display:inline-flex; align-items:center; gap:6px; border:1px solid var(--line); background:var(--surface-2); color:var(--ink); border-radius:999px; padding:7px 13px; font-family:inherit; font-size:12.5px; font-weight:600; cursor:pointer; white-space:nowrap; }
.nf-hero{ display:grid; grid-template-columns:1.15fr .85fr; background:var(--surface); border:1px solid var(--line); border-radius:18px; overflow:hidden; box-shadow:0 1px 0 var(--shadow); margin-bottom:8px; }
.nf-hero-body{ padding:30px 32px; display:flex; flex-direction:column; }
.nf-hero-art{ position:relative; min-height:230px; border-left:1px solid var(--line); }
.nf-tag{ display:inline-flex; align-items:center; gap:7px; font-family:'Bricolage Grotesque',sans-serif; font-size:11px; letter-spacing:.8px; text-transform:uppercase; font-weight:700; flex-wrap:wrap; }
.nf-tag .swatch{ width:8px; height:8px; border-radius:50%; }
.nf-tag .scope{ color:var(--faint); display:inline-flex; align-items:center; gap:4px; }
.nf-hero h1{ font-family:'Bricolage Grotesque',sans-serif; font-weight:600; font-size:34px; line-height:1.1; letter-spacing:-.6px; margin:16px 0 12px; }
.nf-hero p{ color:var(--muted); font-size:16px; line-height:1.6; margin:0 0 20px; max-width:48ch; }
.nf-hero-meta{ margin-top:auto; display:flex; align-items:center; gap:8px; font-family:'Bricolage Grotesque',sans-serif; font-size:12px; color:var(--faint); flex-wrap:wrap; }
.nf-readlink{ display:inline-flex; align-items:center; gap:6px; align-self:flex-start; margin-top:18px; color:var(--accent); font-size:14px; font-weight:600; cursor:pointer; background:none; border:0; font-family:inherit; padding:0; text-decoration:none; }
.nf-readlink:hover{ text-decoration:underline; }
.nf-grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }
.nf-card{ position:relative; background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:20px 20px 18px 22px; display:flex; flex-direction:column; cursor:pointer; transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease; overflow:hidden; }
.nf-card:hover{ transform:translateY(-3px); box-shadow:0 12px 28px var(--shadow); }
.nf-spine{ position:absolute; left:0; top:0; bottom:0; width:0; transition:width .2s ease; }
.nf-card[data-followed="true"] .nf-spine{ width:4px; }
.nf-card h3{ font-family:'Bricolage Grotesque',sans-serif; font-weight:600; font-size:19px; line-height:1.22; letter-spacing:-.3px; margin:11px 0 9px; }
.nf-card p{ color:var(--muted); font-size:13.5px; line-height:1.55; margin:0 0 16px; flex:1; }
.nf-card-foot{ display:flex; align-items:center; justify-content:space-between; gap:8px; font-family:'Bricolage Grotesque',sans-serif; font-size:11.5px; letter-spacing:.2px; color:var(--faint); }
.nf-card-foot .src{ color:var(--muted); font-weight:700; }
.nf-meta-row{ display:flex; align-items:center; gap:6px; }
.nf-following-pill{ display:inline-flex; align-items:center; gap:4px; font-family:'Bricolage Grotesque',sans-serif; font-size:10.5px; font-weight:700; letter-spacing:.3px; text-transform:uppercase; padding:3px 8px; border-radius:999px; background:var(--accent-soft); color:var(--accent); }
.nf-bm{ border:0; background:transparent; color:var(--faint); cursor:pointer; padding:4px; border-radius:8px; transition:color .2s ease; }
.nf-bm:hover{ color:var(--ink); }
.nf-bm[data-on="true"]{ color:var(--accent); }
.nf-empty{ text-align:center; padding:60px 20px; color:var(--muted); }
.nf-empty svg{ color:var(--faint); margin-bottom:14px; }
.nf-empty h3{ font-family:'Bricolage Grotesque',sans-serif; font-weight:600; font-size:22px; color:var(--ink); margin:0 0 8px; }
.nf-empty button{ margin-top:18px; border:1px solid var(--accent); background:var(--accent); color:var(--accent-ink); border-radius:999px; padding:10px 20px; font-family:inherit; font-weight:600; font-size:14px; cursor:pointer; }
.nf-sub{ margin:36px 0; background:var(--ink); color:var(--bg); border-radius:20px; padding:34px 36px; display:grid; grid-template-columns:1fr auto; gap:24px; align-items:center; }
.nf-sub h2{ font-family:'Bricolage Grotesque',sans-serif; font-weight:600; font-size:26px; letter-spacing:-.4px; margin:0 0 8px; }
.nf-sub p{ opacity:.72; font-size:14.5px; line-height:1.55; margin:0; max-width:46ch; }
.nf-sub-form{ display:flex; gap:10px; align-items:center; }
.nf-sub-form input{ border:0; outline:0; border-radius:999px; padding:13px 18px; font-family:inherit; font-size:14px; width:230px; background:var(--bg); color:var(--ink); }
.nf-sub-btn{ display:inline-flex; align-items:center; gap:7px; border:0; border-radius:999px; padding:13px 22px; background:var(--accent); color:var(--accent-ink); font-family:inherit; font-weight:700; font-size:14px; cursor:pointer; white-space:nowrap; transition:filter .2s ease; }
.nf-sub-btn:hover{ filter:brightness(1.06); }
.nf-sub-btn:disabled{ opacity:.6; cursor:default; }
.nf-sub-done{ display:flex; align-items:center; gap:10px; font-size:15px; font-weight:600; }
.nf-sub-done .ring{ width:34px; height:34px; border-radius:50%; background:var(--accent); color:var(--accent-ink); display:inline-flex; align-items:center; justify-content:center; }
.nf-foot{ border-top:1px solid var(--line); padding:26px 0 50px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; color:var(--faint); font-family:'Bricolage Grotesque',sans-serif; font-size:11.5px; }
.nf-toast{ position:fixed; left:50%; bottom:28px; transform:translateX(-50%); background:var(--ink); color:var(--bg); padding:12px 20px; border-radius:999px; font-size:13.5px; font-weight:600; box-shadow:0 12px 30px var(--shadow); z-index:60; display:flex; align-items:center; gap:9px; animation:nf-pop .25s ease; }
@keyframes nf-pop{ from{ opacity:0; transform:translate(-50%,10px);} to{ opacity:1; transform:translate(-50%,0);} }
.nf-skel{ background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:20px; }
.nf-skel .bar{ background:var(--line); border-radius:6px; opacity:.7; animation:nf-pulse 1.3s ease-in-out infinite; }
@keyframes nf-pulse{ 0%,100%{opacity:.45;} 50%{opacity:.85;} }
.nf-spin{ animation:nf-spin 1s linear infinite; }
@keyframes nf-spin{ to{ transform:rotate(360deg);} }
.nf-more{ display:flex; align-items:center; justify-content:center; gap:8px; padding:26px 0 6px; color:var(--muted); font-size:13.5px; font-weight:600; }
.nf-more.nf-end{ color:var(--faint); font-family:'Space Mono',monospace; font-size:12px; letter-spacing:.5px; }
.nf-root :focus-visible{ outline:2px solid var(--accent); outline-offset:2px; border-radius:6px; }
@media (max-width:860px){ .nf-hero{ grid-template-columns:1fr; } .nf-hero-art{ border-left:0; border-top:1px solid var(--line); min-height:150px; order:-1; } .nf-grid{ grid-template-columns:repeat(2,1fr); } .nf-sub{ grid-template-columns:1fr; } .nf-hero h1{ font-size:28px; } }
@media (max-width:560px){ .nf-grid{ grid-template-columns:1fr; } .nf-search{ min-width:0; width:120px; } .nf-word{ font-size:23px; } .nf-hero-body{ padding:24px 22px; } .nf-sub-form{ flex-direction:column; align-items:stretch; } .nf-sub-form input{ width:100%; } }
@media (prefers-reduced-motion:reduce){ .nf-root *{ transition:none !important; animation:none !important; } .nf-card:hover{ transform:none; } }
`;

function HeroArt({ color }) {
  return (
    <svg width="100%" height="100%" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" style={{ position: "absolute", inset: 0 }} aria-hidden="true">
      <defs>
        <linearGradient id="hg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.20" />
          <stop offset="100%" stopColor={color} stopOpacity="0.04" />
        </linearGradient>
      </defs>
      <rect width="400" height="300" fill="url(#hg)" />
      {[...Array(7)].map((_, i) => (
        <line key={i} x1={-40 + i * 70} y1="0" x2={120 + i * 70} y2="300" stroke={color} strokeOpacity="0.14" strokeWidth="1.5" />
      ))}
      {[...Array(3)].map((_, i) => (
        <circle key={i} cx={70 + i * 130} cy={60 + i * 70} r={26 - i * 6} fill="none" stroke={color} strokeOpacity="0.28" strokeWidth="2" />
      ))}
    </svg>
  );
}

function SkeletonCard() {
  return (
    <div className="nf-skel">
      <div className="bar" style={{ height: 10, width: "40%", marginBottom: 16 }} />
      <div className="bar" style={{ height: 16, width: "95%", marginBottom: 8 }} />
      <div className="bar" style={{ height: 16, width: "70%", marginBottom: 18 }} />
      <div className="bar" style={{ height: 10, width: "100%", marginBottom: 6 }} />
      <div className="bar" style={{ height: 10, width: "85%", marginBottom: 20 }} />
      <div className="bar" style={{ height: 10, width: "50%" }} />
    </div>
  );
}

function ArticleCard({ a, color, label, followed, bookmarked, onBookmark }) {
  return (
    <article className="nf-card" data-followed={followed} tabIndex={0}>
      <span className="nf-spine" style={{ background: color }} />
      <div className="nf-tag">
        <span className="swatch" style={{ background: color }} />
        <span style={{ color }}>{label}</span>
        <span className="scope">
          {a.scope === "national" ? <MapPin size={11} /> : <Globe size={11} />}
          {a.scope === "national" ? "National" : "World"}
        </span>
      </div>
      <h3>{a.title}</h3>
      <p>{a.dek}</p>
      <div className="nf-card-foot">
        <div className="nf-meta-row">
          <span className="src">{a.src}</span><span>·</span><span>{timeAgo(a.min)}</span>
        </div>
        <div className="nf-meta-row">
          {followed && <span className="nf-following-pill"><Check size={11} /> Following</span>}
          <button className="nf-bm" data-on={bookmarked} aria-label={bookmarked ? "Remove bookmark" : "Save story"}
            onClick={(e) => { e.stopPropagation(); onBookmark(a.id); }}>
            <Bookmark size={15} fill={bookmarked ? "currentColor" : "none"} />
          </button>
        </div>
      </div>
    </article>
  );
}

export default function Newsfold() {
  const [theme, setTheme] = useState(() => {
    const saved = LS.get("nf_theme", null);
    if (saved === "light" || saved === "dark") return saved;
    try { return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"; }
    catch { return "light"; }
  });
  const [cats, setCats] = useState(FALLBACK_CATEGORIES);
  const [scope, setScope] = useState("national");
  const [activeCat, setActiveCat] = useState("all");
  const [followed, setFollowed] = useState(() => new Set(LS.get("nf_followed", ["technology", "economy"])));
  const [onlyFollowing, setOnlyFollowing] = useState(false);
  const [query, setQuery] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [bookmarks, setBookmarks] = useState(() => new Set(LS.get("nf_bookmarks", [])));

  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tier, setTier] = useState("live");        // live | cached | sample | empty
  const [refreshedAt, setRefreshedAt] = useState(null);
  const [conn, setConn] = useState("ok");          // ok | connecting | down
  const retries = useRef(0);

  const [email, setEmail] = useState(() => LS.get("nf_email", ""));
  const [subState, setSubState] = useState(() => (LS.get("nf_email", "") ? "done" : "idle"));
  const [toast, setToast] = useState(null);
  const toastTimer = useRef(null);

  const catMap = useMemo(() => Object.fromEntries(cats.map((c) => [c.key, c])), [cats]);
  const colorOf = (k) => (catMap[k] && catMap[k].color) || "#8A8A95";
  const labelOf = (k) => (catMap[k] && catMap[k].label) || k;

  const flash = useCallback((msg) => {
    setToast(msg);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 2200);
  }, []);
  useEffect(() => () => clearTimeout(toastTimer.current), []);

  // categories from backend (falls back silently)
  useEffect(() => { getCategories().then((c) => c && c.length && setCats(c)).catch(() => {}); }, []);

  // persist preferences across reloads
  useEffect(() => { LS.set("nf_theme", theme); }, [theme]);
  useEffect(() => { LS.set("nf_followed", [...followed]); }, [followed]);
  useEffect(() => { LS.set("nf_bookmarks", [...bookmarks]); }, [bookmarks]);

  // debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(query), 350);
    return () => clearTimeout(t);
  }, [query]);

  // ----- infinite scroll -----
  const PAGE_SIZE = 30;
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const sentinelRef = useRef(null);

  const fetchPage = useCallback(async (pageNum, replace) => {
    if (replace) setLoading(true); else setLoadingMore(true);
    try {
      const data = await getNews({ scope, category: activeCat, q: debouncedQ, page: pageNum });
      const got = data.articles || [];
      setArticles((prev) => {
        if (replace) return got;
        const seen = new Set(prev.map((a) => a.id));
        return [...prev, ...got.filter((a) => !seen.has(a.id))];
      });
      setTier(data.tier || (data.live ? "live" : "sample"));
      setRefreshedAt(data.refreshed_at || null);
      setHasMore(got.length >= PAGE_SIZE);
      setConn("ok");
      retries.current = 0;
      if (replace) setLoading(false); else setLoadingMore(false);
    } catch {
      if (replace && retries.current < 5) {
        retries.current += 1;
        setConn("connecting");
        setTimeout(() => fetchPage(pageNum, true), 4000);   // keep skeletons up while API wakes
        return;
      }
      if (replace) {
        setArticles(filterSeed({ scope, category: activeCat, q: debouncedQ }));
        setTier("sample"); setRefreshedAt(null); setHasMore(false);
        setConn("ok"); retries.current = 0; setLoading(false);
      } else {
        setHasMore(false); setLoadingMore(false);
      }
    }
  }, [scope, activeCat, debouncedQ]);

  // reset to page 1 whenever filters change
  useEffect(() => { setPage(1); setHasMore(true); fetchPage(1, true); }, [fetchPage]);

  const loadMore = useCallback(() => {
    if (loadingMore || loading || !hasMore) return;
    const next = page + 1;
    setPage(next);
    fetchPage(next, false);
  }, [loadingMore, loading, hasMore, page, fetchPage]);

  // observe the sentinel; load next page as it nears the viewport
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) loadMore(); },
      { rootMargin: "500px" }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [loadMore]);

  const toggleFollow = (key) => setFollowed((prev) => {
    const next = new Set(prev);
    if (next.has(key)) { next.delete(key); flash(`Unfollowed ${labelOf(key)}`); }
    else { next.add(key); flash(`Following ${labelOf(key)} — you'll see more of it`); }
    return next;
  });
  const toggleBookmark = (id) => setBookmarks((prev) => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id); else { next.add(id); flash("Saved to your reading list"); }
    return next;
  });

  const view = useMemo(() => {
    let list = onlyFollowing ? articles.filter((a) => followed.has(a.cat)) : articles.slice();
    list.sort((x, y) => {
      const fx = followed.has(x.cat) ? 0 : 1, fy = followed.has(y.cat) ? 0 : 1;
      if (fx !== fy) return fx - fy;
      return x.min - y.min;
    });
    return list;
  }, [articles, onlyFollowing, followed]);

  const hero = view[0] || null;
  const rest = view.slice(1);

  const handleSubscribe = async () => {
    const addr = email.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(addr)) { flash("Enter a valid email to subscribe"); return; }
    setSubState("sending");
    try {
      const res = await subscribe(addr, [...followed], scope);
      if (res.ok) { setSubState("done"); LS.set("nf_email", addr); flash(res.message); }
      else { setSubState("idle"); flash(res.message); }
    } catch {
      setSubState("idle");
      flash("Couldn't reach the server — try again in a moment");
    }
  };

  const clearFilters = () => { setScope("all"); setActiveCat("all"); setOnlyFollowing(false); setQuery(""); };

  return (
    <div className={`nf-root ${theme}`}>
      <style>{STYLES}</style>

      <header className="nf-mast">
        <div className="nf-wrap">
          <div className="nf-mast-top">
            <div className="nf-brand"><span className="nf-mark" /><span className="nf-word">News<b>fold</b></span></div>
            <div className="nf-tools">
              <div className="nf-search">
                <Search size={16} color="var(--faint)" />
                <input aria-label="Search dispatches" placeholder="Search dispatches" value={query} onChange={(e) => setQuery(e.target.value)} />
              </div>
              <button className="nf-icon-btn" aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}>
                {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
              </button>
            </div>
          </div>
          <div className="nf-kicker">
            <span>Issue · {todayLine()}</span><span className="dot">·</span>
            <span><b>{view.length}</b> dispatches</span><span className="dot">·</span>
            <span><b>{followed.size}</b> followed</span><span className="dot">·</span>
            <span><b>{bookmarks.size}</b> saved</span>
            <span className={`nf-status ${tier}`}>
              {tier === "live" ? <Wifi size={11} /> : tier === "cached" ? <History size={11} /> : <WifiOff size={11} />}
              {tier === "live" ? "Live feed" : tier === "cached" ? "Cached" : "Sample feed"}
            </span>
          </div>
        </div>
      </header>

      <main className="nf-wrap">
        <div className="nf-controls">
          <div className="nf-seg" role="group" aria-label="Coverage scope">
            {[["all", "All", null], ["national", "National", MapPin], ["international", "International", Globe]].map(([val, lbl, Ico]) => (
              <button key={val} aria-pressed={scope === val} onClick={() => setScope(val)}>{Ico && <Ico size={14} />}{lbl}</button>
            ))}
          </div>
          <div className="nf-spacer" />
          <button className="nf-toggle" aria-pressed={onlyFollowing} onClick={() => setOnlyFollowing((v) => !v)}>
            <Check size={14} /> {onlyFollowing ? "Showing followed" : "Followed only"}
          </button>
        </div>

        <div className="nf-chips" role="group" aria-label="News channels">
          <button className="nf-chip-all" data-active={activeCat === "all"} onClick={() => setActiveCat("all")}>All channels</button>
          {cats.map((c) => {
            const isF = followed.has(c.key);
            return (
              <div className="nf-chip" key={c.key} data-active={activeCat === c.key}>
                <button className="pick" aria-pressed={activeCat === c.key} onClick={() => setActiveCat((p) => (p === c.key ? "all" : c.key))}>
                  <span className="swatch" style={{ background: c.color }} />{c.label}
                </button>
                <button className="nf-follow" data-on={isF} aria-label={isF ? `Unfollow ${c.label}` : `Follow ${c.label}`} onClick={() => toggleFollow(c.key)}>
                  {isF ? <><Check size={13} /> Following</> : <><Plus size={13} /> Follow</>}
                </button>
              </div>
            );
          })}
        </div>

        {conn === "connecting" && (
          <div className="nf-banner">
            <RefreshCw size={18} className="nf-spin" style={{ color: "var(--accent)", flex: "0 0 auto" }} />
            <span>Waking the news service… <b>this can take up to a minute</b> on the first request.</span>
          </div>
        )}

        {loading ? (
          <>
            <div className="nf-seclabel">{conn === "connecting" ? "Connecting" : "Loading dispatches"}</div>
            <div className="nf-grid">{[...Array(6)].map((_, i) => <SkeletonCard key={i} />)}</div>
          </>
        ) : view.length === 0 ? (
          <div className="nf-empty">
            <Inbox size={40} />
            <h3>No dispatches match these filters</h3>
            <p>Try a different scope or channel — or clear everything to see the full feed.</p>
            <button onClick={clearFilters}>Clear filters</button>
          </div>
        ) : (
          <>
            {hero && (
              <>
                <div className="nf-seclabel">{onlyFollowing ? "From your channels" : "Lead dispatch"}</div>
                <section className="nf-hero">
                  <div className="nf-hero-body">
                    <div className="nf-tag">
                      <span className="swatch" style={{ background: colorOf(hero.cat) }} />
                      <span style={{ color: colorOf(hero.cat) }}>{labelOf(hero.cat)}</span>
                      <span className="scope">{hero.scope === "national" ? <MapPin size={11} /> : <Globe size={11} />}{hero.scope === "national" ? "National" : "World"}</span>
                      {followed.has(hero.cat) && <span className="nf-following-pill"><Check size={11} /> Following</span>}
                    </div>
                    <h1>{hero.title}</h1>
                    <p>{hero.dek}</p>
                    <div className="nf-hero-meta">
                      <span style={{ color: "var(--muted)", fontWeight: 700 }}>{hero.src}</span><span>·</span>
                      <Clock size={12} /> {timeAgo(hero.min)}<span>·</span>{hero.read} min read
                    </div>
                    {hero.url ? (
                      <a className="nf-readlink" href={hero.url} target="_blank" rel="noreferrer">Read full dispatch <ArrowUpRight size={15} /></a>
                    ) : (
                      <button className="nf-readlink">Read full dispatch <ArrowUpRight size={15} /></button>
                    )}
                  </div>
                  <div className="nf-hero-art"><HeroArt color={colorOf(hero.cat)} /></div>
                </section>
              </>
            )}
            {rest.length > 0 && (
              <>
                <div className="nf-seclabel">More dispatches</div>
                <div className="nf-grid">
                  {rest.map((a) => (
                    <ArticleCard key={a.id} a={a} color={colorOf(a.cat)} label={labelOf(a.cat)}
                      followed={followed.has(a.cat)} bookmarked={bookmarks.has(a.id)} onBookmark={toggleBookmark} />
                  ))}
                </div>
              </>
            )}
            {!loading && (
              <>
                <div ref={sentinelRef} style={{ height: 1 }} />
                {loadingMore && (
                  <div className="nf-more"><RefreshCw size={15} className="nf-spin" /> Loading more…</div>
                )}
                {!hasMore && view.length > 4 && (
                  <div className="nf-more nf-end">You're all caught up</div>
                )}
              </>
            )}
          </>
        )}

        <section className="nf-sub">
          <div>
            <h2>Get the daily dispatch in your inbox</h2>
            <p>One concise edition every morning, tuned to the channels you follow. No noise, unsubscribe anytime.</p>
          </div>
          {subState === "done" ? (
            <div className="nf-sub-done"><span className="ring"><Check size={18} /></span>Subscribed as {email}</div>
          ) : (
            <div className="nf-sub-form">
              <input type="email" aria-label="Email address" placeholder="you@example.com" value={email}
                onChange={(e) => setEmail(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSubscribe()} />
              <button className="nf-sub-btn" onClick={handleSubscribe} disabled={subState === "sending"}>
                <Mail size={16} /> {subState === "sending" ? "Subscribing…" : "Subscribe"}
              </button>
            </div>
          )}
        </section>

        <footer className="nf-foot">
          <span>NEWSFOLD · By Dona Sharma</span>
          <span>
            {tier === "live" && (refreshedAt ? `Updated ${ago(refreshedAt)}` : "Live")}
            {tier === "cached" && `Live feed down · news from ${ago(refreshedAt) || "earlier"}`}
            {tier === "sample" && "Sample feed"}
          </span>
        </footer>
      </main>

      {toast && <div className="nf-toast" role="status"><Check size={15} /> {toast}</div>}
    </div>
  );
}
