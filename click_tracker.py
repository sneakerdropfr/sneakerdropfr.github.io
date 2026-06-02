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
# ── Table de config revenu estimé ─────────────────────────────────────────────
# conversion_rate  : % de clics qui aboutissent à un achat
# commission_rate  : % de commission affilié
# aov              : panier moyen (€)
REVENUE_CONFIG: dict = {
    "BSTN":       {"conversion_rate": 0.02, "commission_rate": 0.08, "aov": 180},
    "Footshop":   {"conversion_rate": 0.02, "commission_rate": 0.07, "aov": 160},
    "SNS":        {"conversion_rate": 0.02, "commission_rate": 0.07, "aov": 170},
    "END":        {"conversion_rate": 0.015,"commission_rate": 0.06, "aov": 200},
    "Asphaltgold":{"conversion_rate": 0.015,"commission_rate": 0.06, "aov": 175},
    "Naked":      {"conversion_rate": 0.015,"commission_rate": 0.06, "aov": 165},
    "Nike":       {"conversion_rate": 0.018,"commission_rate": 0.05, "aov": 150},
    "Adidas":     {"conversion_rate": 0.018,"commission_rate": 0.05, "aov": 130},
    "New Balance":{"conversion_rate": 0.018,"commission_rate": 0.05, "aov": 140},
    "StockX":     {"conversion_rate": 0.025,"commission_rate": 0.03, "aov": 220},
    "GOAT":       {"conversion_rate": 0.025,"commission_rate": 0.03, "aov": 210},
    "Klekt":      {"conversion_rate": 0.02, "commission_rate": 0.04, "aov": 190},
    "_default":   {"conversion_rate": 0.015,"commission_rate": 0.06, "aov": 160},
}

def estimated_revenue(retailer: str, clicks: int) -> float:
    """Revenu estimé = clics × conversion × commission × AOV"""
    cfg = REVENUE_CONFIG.get(retailer, REVENUE_CONFIG["_default"])
    return round(clicks * cfg["conversion_rate"] * cfg["commission_rate"] * cfg["aov"], 2)

def infer_brand_from_id(release_id: str) -> str:
    """Infère la marque depuis le release_id."""
    t = release_id.lower()
    if "jordan" in t or "air-jordan" in t: return "Jordan"
    if "adidas" in t or "samba" in t or "stan-smith" in t or "yeezy" in t or "gazelle" in t or "adizero" in t: return "Adidas"
    if "new-balance" in t or "-nb-" in t: return "New Balance"
    if "asics" in t or "gel-" in t: return "Asics"
    if "converse" in t or "chuck-taylor" in t: return "Converse"
    if "puma" in t or "speedcat" in t: return "Puma"
    if "nike" in t or "dunk" in t or "air-force" in t or "air-max" in t or "blazer" in t or "pegasus" in t: return "Nike"
    return "Other"

@app.get("/stats")
async def get_stats(request: Request, days: int = 30):
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

    # Revenu estimé par retailer
    top_retailers_with_rev = []
    for r in top_retailers:
        cnt = r["cnt"]
        retailer = r["retailer"]
        rev = estimated_revenue(retailer, cnt)
        top_retailers_with_rev.append({"retailer": retailer, "cnt": cnt, "revenue_est": rev})

    total_revenue_est = sum(x["revenue_est"] for x in top_retailers_with_rev)

    # Statistiques par marque
    brand_counts: dict = {}
    for r in top_releases:
        brand = infer_brand_from_id(r["release_id"])
        brand_counts[brand] = brand_counts.get(brand, 0) + r["cnt"]
    # Ajouter les clics non couverts par top_releases (si total > somme top20)
    by_brand = sorted(
        [{"brand": b, "cnt": c} for b, c in brand_counts.items()],
        key=lambda x: x["cnt"], reverse=True
    )

    return JSONResponse({
        "period_days": days,
        "total_clicks": total,
        "total_revenue_est": round(total_revenue_est, 2),
        "by_type": {
            "retail": by_type["retail"] or 0,
            "resell": by_type["resell"] or 0,
            "raffle": by_type["raffle"] or 0,
        },
        "top_releases":  [dict(r) for r in top_releases],
        "top_retailers": top_retailers_with_rev,
        "by_brand":      by_brand,
        "by_day":        [dict(r) for r in by_day],
    })

# ── GET /health ────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "db": str(DB_PATH)}


# ── GET /export ────────────────────────────────────────────────────────────────
@app.get("/export")
async def export_csv(request: Request, days: int = 90):
    if ADMIN_TOKEN:
        token = request.headers.get("X-Admin-Token") or request.query_params.get("token")
        if token != ADMIN_TOKEN:
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse("Accès refusé", status_code=401)

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    with get_db() as db:
        rows = db.execute(
            "SELECT ts, release_id, retailer, url, is_resell, is_raffle FROM clicks "
            "WHERE ts >= ? ORDER BY ts DESC",
            (since,),
        ).fetchall()

    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "release_id", "brand", "retailer", "type", "url"])
    for row in rows:
        rtype = "resell" if row["is_resell"] else ("raffle" if row["is_raffle"] else "retail")
        brand = infer_brand_from_id(row["release_id"])
        writer.writerow([row["ts"][:19], row["release_id"], brand, row["retailer"], rtype, row["url"]])

    from fastapi.responses import StreamingResponse
    output.seek(0)
    filename = f"sneakerdropfr_clics_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ── GET /admin ─────────────────────────────────────────────────────────────────
ADMIN_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SneakerDrop FR — Dashboard Business</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  :root{--r:#FF2D2D;--bg:#0A0A0A;--card:#141414;--card2:#1a1a1a;--border:#222;--txt:#fff;--muted:#888;--green:#4ade80;--yellow:#fbbf24}
  body{background:var(--bg);color:var(--txt);font-family:'Segoe UI',system-ui,sans-serif;padding:2rem;max-width:1200px;margin:0 auto}
  h1{font-size:1.4rem;font-weight:900;letter-spacing:.05em;margin-bottom:.3rem}
  h1 span{color:var(--r)}
  .toolbar{display:flex;align-items:center;gap:1rem;margin-bottom:2rem;flex-wrap:wrap}
  .sub{color:var(--muted);font-size:.85rem;flex:1}
  select{background:#1a1a1a;color:#fff;border:1px solid var(--border);border-radius:6px;padding:.4rem .75rem;font-size:.85rem}
  .btn{display:inline-flex;align-items:center;gap:.4rem;background:#1a1a1a;color:#fff;border:1px solid var(--border);border-radius:6px;padding:.4rem .9rem;font-size:.82rem;font-weight:600;cursor:pointer;transition:border-color .15s,background .15s;text-decoration:none}
  .btn:hover{border-color:#fff;background:#222}
  .btn--accent{background:var(--r);border-color:var(--r)}
  .btn--accent:hover{background:#cc2222;border-color:#cc2222}
  /* KPIs */
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem;margin-bottom:2rem}
  .kpi{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:1.2rem 1.4rem}
  .kpi__val{font-size:1.9rem;font-weight:900;line-height:1}
  .kpi__lbl{color:var(--muted);font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;margin-top:.3rem}
  .kpi--accent .kpi__val{color:var(--r)}
  .kpi--green .kpi__val{color:var(--green)}
  /* Layout 2 colonnes */
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:1.5rem}
  @media(max-width:700px){.cols{grid-template-columns:1fr}}
  .panel{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:1.25rem}
  .panel h2{font-size:.78rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:1rem}
  /* Chart */
  .chart{display:flex;align-items:flex-end;gap:3px;height:80px}
  .chart-bar{flex:1;background:var(--r);border-radius:3px 3px 0 0;min-height:2px;position:relative;cursor:default;opacity:.8;transition:opacity .15s}
  .chart-bar:hover{opacity:1}
  .chart-bar:hover::after{content:attr(data-tip);position:absolute;bottom:110%;left:50%;transform:translateX(-50%);background:#333;color:#fff;font-size:.65rem;padding:.2rem .45rem;border-radius:4px;white-space:nowrap;z-index:10}
  /* Tables */
  table{width:100%;border-collapse:collapse}
  th{text-align:left;font-size:.65rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding:.45rem .5rem;border-bottom:1px solid var(--border)}
  td{padding:.55rem .5rem;border-bottom:1px solid #1a1a1a;font-size:.88rem}
  tr:last-child td{border-bottom:none}
  .bar-wrap{background:#1e1e1e;border-radius:4px;height:5px;margin-top:.3rem;overflow:hidden;min-width:60px}
  .bar{background:var(--r);height:100%;border-radius:4px}
  .bar--green{background:var(--green)}
  .rev{color:var(--green);font-weight:700}
  /* Badges type */
  .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:.35rem}
  .dot--retail{background:var(--green)}
  .dot--resell{background:var(--r)}
  .dot--raffle{background:var(--yellow)}
  /* Brand doughnut simulé */
  .brand-list{display:flex;flex-direction:column;gap:.6rem}
  .brand-row{display:flex;align-items:center;gap:.75rem}
  .brand-name{font-size:.85rem;font-weight:600;min-width:100px}
  .brand-bar-wrap{flex:1;background:#1e1e1e;border-radius:4px;height:8px;overflow:hidden}
  .brand-bar{height:100%;border-radius:4px;background:var(--r)}
  .brand-cnt{font-size:.8rem;color:var(--muted);min-width:40px;text-align:right}
  .brand-pct{font-size:.75rem;color:var(--muted);min-width:40px;text-align:right}
  /* Revenue config note */
  .note{font-size:.72rem;color:var(--muted);margin-top:.75rem;line-height:1.5;padding:.6rem .8rem;background:#111;border-radius:6px;border:1px solid #1e1e1e}
  .loading{color:var(--muted);font-size:.9rem;padding:2rem 0;text-align:center}
  /* Full-width panels */
  .full{margin-bottom:1.5rem}
</style>
</head>
<body>
<h1>SneakerDrop <span>FR</span> — Dashboard Business</h1>

<div class="toolbar">
  <span class="sub" id="updated">Chargement…</span>
  <select id="period" onchange="load()">
    <option value="7">7 derniers jours</option>
    <option value="30" selected>30 derniers jours</option>
    <option value="90">90 derniers jours</option>
  </select>
  <a id="export-btn" href="#" class="btn btn--accent" onclick="exportCsv(event)">⬇ Export CSV</a>
</div>

<div class="kpis" id="kpis"><div class="loading">Chargement…</div></div>

<div class="cols">
  <div class="panel full">
    <h2>Clics par jour</h2>
    <div class="chart" id="chart"></div>
  </div>
  <div class="panel full">
    <h2>Répartition type</h2>
    <div id="type-viz"></div>
  </div>
</div>

<div class="cols">
  <div class="panel">
    <h2>Top retailers — revenu estimé</h2>
    <table>
      <thead><tr><th>#</th><th>Retailer</th><th>Clics</th><th>Revenu est.</th><th></th></tr></thead>
      <tbody id="tbl-retailers"></tbody>
    </table>
    <div class="note">Revenu estimé = clics × taux conv. × commission × panier moyen. Approximatif.</div>
  </div>
  <div class="panel">
    <h2>Clics par marque</h2>
    <div class="brand-list" id="brand-list"></div>
  </div>
</div>

<div class="panel full">
  <h2>Top paires</h2>
  <table>
    <thead><tr><th>#</th><th>Paire</th><th>Marque</th><th>Clics</th><th></th></tr></thead>
    <tbody id="tbl-releases"></tbody>
  </table>
</div>

<script>
const TOKEN = new URLSearchParams(location.search).get('token') || '';

const BRAND_COLORS = {
  'Jordan':'#FF2D2D','Nike':'#FF6B35','Adidas':'#4ade80',
  'New Balance':'#60a5fa','Asics':'#a78bfa','Puma':'#fbbf24',
  'Converse':'#f472b6','Other':'#888'
};

function infer_brand(rid) {
  const t = rid.toLowerCase();
  if(t.includes('jordan')||t.includes('air-jordan')) return 'Jordan';
  if(t.includes('adidas')||t.includes('samba')||t.includes('stan-smith')||t.includes('yeezy')||t.includes('gazelle')) return 'Adidas';
  if(t.includes('new-balance')) return 'New Balance';
  if(t.includes('asics')||t.includes('gel-')) return 'Asics';
  if(t.includes('converse')||t.includes('chuck-taylor')) return 'Converse';
  if(t.includes('puma')||t.includes('speedcat')) return 'Puma';
  if(t.includes('nike')||t.includes('dunk')||t.includes('air-force')||t.includes('air-max')||t.includes('blazer')) return 'Nike';
  return 'Other';
}

function fmt_rev(v) {
  if(v===0) return '—';
  return v < 1 ? '<1 €' : Math.round(v) + ' €';
}

async function load() {
  const days = document.getElementById('period').value;
  const url = `/stats?days=${days}${TOKEN ? '&token='+TOKEN : ''}`;
  const res = await fetch(url);
  if(!res.ok){ document.body.innerHTML='<p style="color:#f87171;padding:2rem">Accès refusé</p>'; return; }
  const d = await res.json();

  document.getElementById('updated').textContent =
    `Mis à jour : ${new Date().toLocaleTimeString('fr-FR')} — ${days} jours`;

  // KPIs
  const revStr = d.total_revenue_est > 0 ? Math.round(d.total_revenue_est) + ' €' : '0 €';
  const topRetailer = d.top_retailers[0];
  document.getElementById('kpis').innerHTML = `
    <div class="kpi kpi--accent"><div class="kpi__val">${d.total_clicks}</div><div class="kpi__lbl">Clics totaux</div></div>
    <div class="kpi kpi--green"><div class="kpi__val">${revStr}</div><div class="kpi__lbl">Revenu estimé</div></div>
    <div class="kpi"><div class="kpi__val">${d.by_type.retail}</div><div class="kpi__lbl">Retail</div></div>
    <div class="kpi"><div class="kpi__val">${d.by_type.resell}</div><div class="kpi__lbl">Resell</div></div>
    <div class="kpi"><div class="kpi__val">${d.by_type.raffle}</div><div class="kpi__lbl">Raffle</div></div>
    <div class="kpi"><div class="kpi__val">${topRetailer ? topRetailer.retailer : '—'}</div><div class="kpi__lbl">#1 Retailer</div></div>
    <div class="kpi"><div class="kpi__val">${d.top_releases[0] ? d.top_releases[0].release_id.split('-').slice(0,4).join(' ') : '—'}</div><div class="kpi__lbl">#1 Paire</div></div>
  `;

  // Chart clics/jour
  const byDay = [...d.by_day].reverse();
  const maxVal = Math.max(...byDay.map(x=>x.cnt), 1);
  document.getElementById('chart').innerHTML = byDay.map(x => {
    const h = Math.max(Math.round(x.cnt/maxVal*100), 2);
    return `<div class="chart-bar" style="height:${h}%" data-tip="${x.day}: ${x.cnt}"></div>`;
  }).join('') || '<div style="color:var(--muted);font-size:.8rem;margin:auto">Aucune donnée</div>';

  // Type viz
  const total = d.total_clicks || 1;
  const retailPct = Math.round(d.by_type.retail/total*100);
  const resellPct = Math.round(d.by_type.resell/total*100);
  const rafflePct = Math.round(d.by_type.raffle/total*100);
  document.getElementById('type-viz').innerHTML = `
    <div style="display:flex;flex-direction:column;gap:.75rem;margin-top:.5rem">
      <div><div style="display:flex;justify-content:space-between;margin-bottom:.3rem"><span><span class="dot dot--retail"></span>Retail</span><span>${d.by_type.retail} (${retailPct}%)</span></div><div class="bar-wrap" style="height:8px"><div class="bar bar--green" style="width:${retailPct}%"></div></div></div>
      <div><div style="display:flex;justify-content:space-between;margin-bottom:.3rem"><span><span class="dot dot--resell"></span>Resell</span><span>${d.by_type.resell} (${resellPct}%)</span></div><div class="bar-wrap" style="height:8px"><div class="bar" style="width:${resellPct}%"></div></div></div>
      <div><div style="display:flex;justify-content:space-between;margin-bottom:.3rem"><span><span class="dot dot--raffle"></span>Raffle</span><span>${d.by_type.raffle} (${rafflePct}%)</span></div><div class="bar-wrap" style="height:8px"><div class="bar" style="background:var(--yellow);width:${rafflePct}%"></div></div></div>
    </div>`;

  // Top retailers + revenu
  const maxCnt = d.top_retailers[0]?.cnt || 1;
  const maxRev = Math.max(...d.top_retailers.map(r=>r.revenue_est), 1);
  document.getElementById('tbl-retailers').innerHTML = d.top_retailers.map((r,i) => `
    <tr>
      <td style="color:var(--muted);width:24px">${i+1}</td>
      <td><strong>${r.retailer}</strong></td>
      <td>${r.cnt}</td>
      <td class="rev">${fmt_rev(r.revenue_est)}</td>
      <td style="width:80px"><div class="bar-wrap"><div class="bar bar--green" style="width:${Math.round(r.revenue_est/maxRev*100)}%"></div></div></td>
    </tr>`).join('') || '<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:1rem">Aucune donnée</td></tr>';

  // Par marque
  const brands = d.by_brand || [];
  const maxBrand = brands[0]?.cnt || 1;
  const brandTotal = brands.reduce((s,b)=>s+b.cnt, 0) || 1;
  document.getElementById('brand-list').innerHTML = brands.map(b => {
    const pct = Math.round(b.cnt/brandTotal*100);
    const color = BRAND_COLORS[b.brand] || '#888';
    return `<div class="brand-row">
      <div class="brand-name">${b.brand}</div>
      <div class="brand-bar-wrap"><div class="brand-bar" style="width:${Math.round(b.cnt/maxBrand*100)}%;background:${color}"></div></div>
      <div class="brand-cnt">${b.cnt}</div>
      <div class="brand-pct">${pct}%</div>
    </div>`;
  }).join('') || '<div style="color:var(--muted);font-size:.85rem">Aucune donnée</div>';

  // Top releases
  const maxR = d.top_releases[0]?.cnt || 1;
  document.getElementById('tbl-releases').innerHTML = d.top_releases.map((r,i) => {
    const brand = infer_brand(r.release_id);
    const color = BRAND_COLORS[brand] || '#888';
    const label = r.release_id.replace(/-/g,' ');
    return `<tr>
      <td style="color:var(--muted);width:24px">${i+1}</td>
      <td><a href="https://sneakerdropfr.fr/sorties/${r.release_id}.html" target="_blank" style="color:#fff">${label}</a></td>
      <td><span style="color:${color};font-size:.78rem;font-weight:700">${brand}</span></td>
      <td><strong>${r.cnt}</strong></td>
      <td style="width:100px"><div class="bar-wrap"><div class="bar" style="width:${Math.round(r.cnt/maxR*100)}%"></div></div></td>
    </tr>`;
  }).join('') || '<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:1rem">Aucune donnée</td></tr>';
}

function exportCsv(e) {
  e.preventDefault();
  const days = document.getElementById('period').value;
  window.location.href = `/export?days=${days}${TOKEN ? '&token='+TOKEN : ''}`;
}

load();
setInterval(load, 60000);
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
