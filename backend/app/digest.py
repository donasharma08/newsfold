"""Builds and sends the personalised daily digest.

Pulls each subscriber's followed channels from the rolling news store, renders
a simple HTML email, and sends it. Triggered by POST /api/digest/run (guarded
by a token), which you wire to a free external cron.
"""

import hmac
import hashlib
import logging
from datetime import datetime, timezone
from urllib.parse import quote

from .config import settings
from .categories import CATEGORIES, CANON

log = logging.getLogger("newsfold.digest")
_LABEL = {c["key"]: c["label"] for c in CATEGORIES}
_COLOR = {c["key"]: c["color"] for c in CATEGORIES}


def unsub_token(email: str) -> str:
    secret = (settings.digest_token or "newsfold").encode()
    return hmac.new(secret, email.lower().encode(), hashlib.sha256).hexdigest()[:16]


def verify_unsub(email: str, token: str) -> bool:
    return hmac.compare_digest(unsub_token(email), token or "")


def _collect(store, sub: dict, per_channel: int = 3):
    channels = sub["channels"] or [c["key"] for c in CATEGORIES]
    scope = sub.get("scope") or "all"
    grouped: list[tuple[str, list]] = []
    seen = set()
    for ch in channels:
        if ch not in CANON:
            continue
        items = []
        for a in store.recent(scope, ch, "", settings.retention_hours, limit=per_channel):
            if a.id in seen:
                continue
            seen.add(a.id)
            items.append(a)
        if items:
            grouped.append((ch, items))
    return grouped


def _render(sub: dict, grouped) -> str:
    today = datetime.now(timezone.utc).strftime("%A, %d %B %Y")
    email = sub["email"]
    unsub = f"{settings.api_base_url}/api/unsubscribe?email={quote(email)}&t={unsub_token(email)}"

    sections = []
    for ch, items in grouped:
        rows = []
        for a in items:
            link = a.url or settings.app_base_url
            rows.append(f"""
              <tr><td style="padding:10px 0;border-bottom:1px solid #eceae5;">
                <a href="{link}" style="color:#15151b;text-decoration:none;font-weight:600;font-size:16px;line-height:1.3;">{a.title}</a>
                <div style="color:#5c5c68;font-size:13px;line-height:1.5;margin-top:4px;">{a.dek or ""}</div>
                <div style="color:#8a8a95;font-size:11px;margin-top:5px;text-transform:uppercase;letter-spacing:.4px;">{a.src}</div>
              </td></tr>""")
        sections.append(f"""
          <table width="100%" cellpadding="0" cellspacing="0" style="margin:22px 0 4px;">
            <tr><td style="border-left:3px solid {_COLOR.get(ch,'#8b2332')};padding-left:10px;
                 font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:{_COLOR.get(ch,'#8b2332')};">
              {_LABEL.get(ch, ch)}</td></tr>
          </table>
          <table width="100%" cellpadding="0" cellspacing="0">{''.join(rows)}</table>""")

    body = "".join(sections) or '<p style="color:#5c5c68;">No fresh dispatches in your channels today.</p>'
    return f"""<!doctype html><html><body style="margin:0;background:#f5f4f0;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f4f0;padding:28px 0;">
        <tr><td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:14px;
               border:1px solid #e6e4de;padding:30px 34px;font-family:Helvetica,Arial,sans-serif;">
            <tr><td style="font-size:22px;font-weight:800;letter-spacing:-.5px;color:#15151b;">
              News<span style="color:#8b2332;">fold</span></td></tr>
            <tr><td style="font-size:12px;color:#8a8a95;padding-top:4px;">Your daily dispatch · {today}</td></tr>
            <tr><td>{body}</td></tr>
            <tr><td style="padding-top:24px;border-top:1px solid #eceae5;font-size:11px;color:#8a8a95;">
              You follow {len(grouped)} channel(s). <a href="{unsub}" style="color:#8b2332;">Unsubscribe</a>.
            </td></tr>
          </table>
        </td></tr>
      </table></body></html>"""


def build_preview(store, email: str) -> str:
    subs = {s["email"]: s for s in store.list_subscribers()}
    sub = subs.get(email.lower()) or {"email": email, "channels": [], "scope": "all"}
    return _render(sub, _collect(store, sub))


def run_digest(store) -> dict:
    from .email_sender import send_email
    subs = store.list_subscribers()
    sent = 0
    for sub in subs:
        grouped = _collect(store, sub)
        if not grouped:
            continue
        html = _render(sub, grouped)
        if send_email(sub["email"], "Your Newsfold daily dispatch", html):
            sent += 1
    log.info("digest run: %d subscribers, %d sent", len(subs), sent)
    return {"subscribers": len(subs), "sent": sent}
