#!/usr/bin/env python3
"""
SneakerDrop FR — Click Tracker
FastAPI + SQLite server-side click tracking for retailer links.

Endpoints:
  POST /click          — record a click event
  GET  /stats          — JSON stats (last 30 days)
  GET  /admin          — HTML dashboard
  GET  /health         — liveness check

Usage:
  pip install fastapi uvicorn
  python click_tracker.py

Default port: 8421
"""

import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

# ── Config ─────────────────────────────────────────────────────────────────────
PORT        = int(os.getenv("TRACKER_PORT", 8421))
DB_PATH     = Path(os.getenv("TRACKER_DB", "/var/data/clicks.db"))
SITE_ORIGIN = os.getenv("SITE_ORIGIN", "https://sneakerdropfr.fr")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")   # vide = pas de protection (à changer en prod)

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── DB helpers ─────────────────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS clicks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          TEXT    NOT NULL,          -- ISO 8601 UTC
                release_id  TEXT    NOT NULL,          -- e.g. air-jordan-3-retro-true-blue
                retailer    TEXT    NOT NULL,          -- e.g. BSTN, GOAT, Nike
                url         TEXT    NOT NULL,
                is_resell   INTEGER NOT NULL DEFAULT 0,
                is_raffle   INTEGER NOT NULL DEFAULT 0,
                referrer    TEXT,
                ua          TEXT
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_ts         ON clicks(ts)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_release    ON clicks(release_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_retailer   ON clicks(retailer)")
        db.commit()

# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="SneakerDrop FR Click Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[SITE_ORIGIN, "http://localhost"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# ── POST /click ────────────────────────────────────────────────────────────────
@app.post("/click")
async def record_click(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid JSON"}, status_code=400)

    release_id = str(body.get("release_id", "")).strip()[:120]
    retailer   = str(body.get("retailer",   "")).strip()[:80]
    url        = str(body.get("url",        "")).strip()[:500]
    is_resell  = int(bool(body.get("is_resell", False)))
    is_raffle  = int(bool(body.get("is_raffle", False)))

    if not release_id or not retailer or not url:
        return JSONResponse({"ok": False, "error": "missing fields"}, status_code=422)

    ts       = datetime.now(timezone.utc).isoformat()
    referrer = str(request.headers.get("referer", ""))[:200]
    ua       = str(request.headers.get("user-agent", ""))[:200]

    with get_db() as db:
        db.execute(
            "INSERT INTO clicks (ts, release_id, retailer, url, is_resell, is_raffle, referrer, ua) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ts, release_id, retailer, url, is_resell, is_raffle, referrer, ua),
        )
        db.commit()

    return JSONResponse({"ok": True})

# ── GET /stats ─────────────────────────────────────────────────────────────────
@app.get("/stats")
async def get_stats(request: Request, days: int = 30):
    # Protection optionnelle par token
    if ADMIN_TOKEN:
        token = request.headers.get("X-Admin-Token") or request.query_params.get("token")
        if token != ADMIN_TOKEN:
            return JSONResponse({"error": "unauthorized"}, status_code=401)

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    with get_db() as db:
        total = db.execute(
            "SELECT COUNT(*) FROM clicks WHERE ts >= ?", (since,)
        ).fetchone()[0]

        top_releases = db.execute(
            "SELECT release_id, COUNT(*) as cnt FROM clicks WHERE ts >= ? "
            "GROUP BY release_id ORDER BY cnt DESC LIMIT 20",
            (since,),
        ).fetchall()

        top_retailers = db.execute(
            "SELECT retailer, COUNT(*) as cnt FROM clicks WHERE ts >= ? "
            "GROUP BY retailer ORDER BY cnt DESC LIMIT 20",
            (since,),
        ).fetchall()

        by_day = db.execute(
            "SELECT substr(ts,1,10) as day, COUNT(*) as cnt FROM clicks WHERE ts >= ? "
            "GROUP BY day ORDER BY day DESC LIMIT 30",
            (since,),
        ).fetchall()

        by_type = db.execute(
            "SELECT "
            "  SUM(CASE WHEN is_resell=0 AND is_raffle=0 THEN 1 ELSE 0 END) as retail, "
            "  SUM(is_resell) as resell, "
            "  SUM(is_raffle) as raffle "
            "FROM clicks WHERE ts >= ?",
            (since,),
        ).fetchone()

    return JSONResponse({
        "period_days": days,
        "total_clicks": total,
        "by_type": {
            "retail": by_type["retail"] or 0,
            "resell": by_type["resell"] or 0,
            "raffle": by_type["raffle"] or 0,
        },
        "top_releases":  [dict(r) for r in top_releases],
        "top_retailers": [dict(r) for r in top_retailers],
        "by_day":        [dict(r) for r in by_day],
    })

# ── GET /health ────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "db": str(DB_PATH)}

# ── GET /admin ─────────────────────────────────────────────────────────────────
ADMIN_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SneakerDrop FR — Clics Retailers</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  :root{--r:#FF2D2D;--bg:#0A0A0A;--card:#141414;--border:#222;--txt:#fff;--muted:#888}
  body{background:var(--bg);color:var(--txt);font-family:'Segoe UI',system-ui,sans-serif;padding:2rem}
  h1{font-size:1.4rem;font-weight:900;letter-spacing:.05em;margin-bottom:.3rem}
  h1 span{color:var(--r)}
  .sub{color:var(--muted);font-size:.85rem;margin-bottom:2rem}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem;margin-bottom:2rem}
  .kpi{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:1.2rem 1.5rem}
  .kpi__val{font-size:2rem;font-weight:900;line-height:1}
  .kpi__lbl{color:var(--muted);font-size:.75rem;text-transform:uppercase;letter-spacing:.07em;margin-top:.3rem}
  .kpi--accent .kpi__val{color:var(--r)}
  section{margin-bottom:2.5rem}
  h2{font-size:1rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;margin-bottom:1rem;color:var(--muted)}
  table{width:100%;border-collapse:collapse}
  th{text-align:left;font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding:.5rem .75rem;border-bottom:1px solid var(--border)}
  td{padding:.6rem .75rem;border-bottom:1px solid var(--border);font-size:.9rem}
  tr:last-child td{border-bottom:none}
  .bar-wrap{background:#1e1e1e;border-radius:4px;height:6px;margin-top:.3rem;overflow:hidden}
  .bar{background:var(--r);height:100%;border-radius:4px;transition:width .4s}
  .badge{display:inline-block;padding:.15rem .5rem;border-radius:999px;font-size:.65rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase}
  .badge-retail{background:#0d3320;color:#4ade80}
  .badge-resell{background:#3d0e0e;color:#f87171}
  .badge-raffle{background:#2d2200;color:#fbbf24}
  .chart{display:flex;align-items:flex-end;gap:3px;height:80px;margin-top:.5rem}
  .chart-bar{flex:1;background:var(--r);border-radius:3px 3px 0 0;min-height:2px;position:relative;cursor:default}
  .chart-bar:hover::after{content:attr(data-tip);position:absolute;bottom:110%;left:50%;transform:translateX(-50%);background:#222;color:#fff;font-size:.65rem;padding:.2rem .45rem;border-radius:4px;white-space:nowrap}
  select{background:#1a1a1a;color:#fff;border:1px solid var(--border);border-radius:6px;padding:.4rem .75rem;font-size:.85rem;margin-bottom:1rem}
  .loading{color:var(--muted);font-size:.9rem;padding:2rem 0;text-align:center}
</style>
</head>
<body>
<h1>SneakerDrop <span>FR</span> — Clics Retailers</h1>
<p class="sub" id="updated">Chargement…</p>

<select id="period" onchange="load()">
  <option value="7">7 derniers jours</option>
  <option value="30" selected>30 derniers jours</option>
  <option value="90">90 derniers jours</option>
</select>

<div class="grid" id="kpis"><div class="loading">Chargement…</div></div>

<section>
  <h2>Clics par jour</h2>
  <div class="chart" id="chart"></div>
</section>

<section>
  <h2>Top paires</h2>
  <table><thead><tr><th>#</th><th>Release</th><th>Clics</th><th></th></tr></thead>
  <tbody id="tbl-releases"></tbody></table>
</section>

<section>
  <h2>Top retailers</h2>
  <table><thead><tr><th>#</th><th>Retailer</th><th>Clics</th><th></th></tr></thead>
  <tbody id="tbl-retailers"></tbody></table>
</section>

<script>
const TOKEN = new URLSearchParams(location.search).get('token') || '';

async function load() {
  const days = document.getElementById('period').value;
  const url = `/stats?days=${days}${TOKEN ? '&token='+TOKEN : ''}`;
  const res = await fetch(url);
  if (!res.ok) { document.body.innerHTML = '<p style="color:#f87171;padding:2rem">Accès refusé</p>'; return; }
  const d = await res.json();

  document.getElementById('updated').textContent =
    `Mis à jour : ${new Date().toLocaleTimeString('fr-FR')} — période : ${days} jours`;

  // KPIs
  const total = d.total_clicks;
  document.getElementById('kpis').innerHTML = `
    <div class="kpi kpi--accent"><div class="kpi__val">${total}</div><div class="kpi__lbl">Clics totaux</div></div>
    <div class="kpi"><div class="kpi__val">${d.by_type.retail}</div><div class="kpi__lbl">Retail</div></div>
    <div class="kpi"><div class="kpi__val">${d.by_type.resell}</div><div class="kpi__lbl">Resell</div></div>
    <div class="kpi"><div class="kpi__val">${d.by_type.raffle}</div><div class="kpi__lbl">Raffle</div></div>
    <div class="kpi"><div class="kpi__val">${d.top_releases.length ? d.top_releases[0].release_id.split('-').slice(0,3).join(' ') : '—'}</div><div class="kpi__lbl">#1 paire</div></div>
  `;

  // Chart
  const byDay = [...d.by_day].reverse();
  const maxVal = Math.max(...byDay.map(x => x.cnt), 1);
  document.getElementById('chart').innerHTML = byDay.map(x => {
    const h = Math.round((x.cnt / maxVal) * 100);
    return `<div class="chart-bar" style="height:${h}%" data-tip="${x.day}: ${x.cnt} clics"></div>`;
  }).join('');

  // Top releases
  const maxR = d.top_releases[0]?.cnt || 1;
  document.getElementById('tbl-releases').innerHTML = d.top_releases.map((r, i) => `
    <tr>
      <td style="color:var(--muted)">${i+1}</td>
      <td><a href="https://sneakerdropfr.fr/sorties/${r.release_id}.html" target="_blank"
           style="color:#fff;text-decoration:none">${r.release_id}</a></td>
      <td><strong>${r.cnt}</strong></td>
      <td style="width:120px"><div class="bar-wrap"><div class="bar" style="width:${Math.round(r.cnt/maxR*100)}%"></div></div></td>
    </tr>`).join('');

  // Top retailers
  const maxRt = d.top_retailers[0]?.cnt || 1;
  document.getElementById('tbl-retailers').innerHTML = d.top_retailers.map((r, i) => `
    <tr>
      <td style="color:var(--muted)">${i+1}</td>
      <td>${r.retailer}</td>
      <td><strong>${r.cnt}</strong></td>
      <td style="width:120px"><div class="bar-wrap"><div class="bar" style="width:${Math.round(r.cnt/maxRt*100)}%"></div></div></td>
    </tr>`).join('');
}

load();
setInterval(load, 60000); // refresh auto toutes les 60s
</script>
</body>
</html>
"""

@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    if ADMIN_TOKEN:
        token = request.query_params.get("token")
        if token != ADMIN_TOKEN:
            return HTMLResponse("<p>Accès refusé</p>", status_code=401)
    return HTMLResponse(ADMIN_HTML)

# ── Entrypoint ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("click_tracker:app", host="0.0.0.0", port=PORT, reload=False)
