#!/usr/bin/env python3
"""Liens HTML internes pour le référencement (lancé au déploiement GitHub Pages, avant la construction).

- Ajoute un bloc de vrais liens vers les fiches /sorties/ dans index.html, sorties.html et categories/*.html
  (entre <!-- SEO-LINKS:START --> et <!-- SEO-LINKS:END -->, remplacé à chaque passage).
- Crée toutes-les-sorties.html : calendrier complet, sorties à venir puis passées, avec un lien vers chaque fiche.
- Ajoute toutes-les-sorties.html au sitemap.xml s'il n'y est pas.
Ne touche qu'aux fichiers du dossier de travail du déploiement : rien n'est commité.
"""
import json, os, re, sys
from datetime import date
from html import escape

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
SITE = "https://sneakerdropfr.fr"
ARCHIVE = "toutes-les-sorties.html"
COURT = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
START, END = "<!-- SEO-LINKS:START -->", "<!-- SEO-LINKS:END -->"
JORDAN = {"air jordan", "jordan", "jordan brand"}
CATS = {
    "nike": lambda e: brand(e) == "nike" and not is_jordan(e),
    "jordan": lambda e: is_jordan(e),
    "adidas": lambda e: brand(e) == "adidas",
    "new-balance": lambda e: brand(e) == "new balance",
}
CAT_NAMES = {"nike": "Nike", "jordan": "Jordan", "adidas": "Adidas", "new-balance": "New Balance"}


def brand(e): return (e.get("brand") or "").strip().lower()
def is_jordan(e): return brand(e) in JORDAN or (e.get("title") or "").lower().startswith("air jordan")


def load(fn):
    p = os.path.join(ROOT, fn)
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return []


def clean_title(t):
    return re.sub(r"\s+", " ", (t or "").replace("\xa0", " ")).strip()


def collect():
    today = date.today().isoformat()
    seen, up, past = set(), [], []
    for e in load("releases.json") + load("releases_past.json"):
        i = e.get("id") or ""
        if not i or i in seen or not re.fullmatch(r"[A-Za-z0-9._-]+", i):
            continue
        if not os.path.exists(os.path.join(ROOT, "sorties", i + ".html")):
            continue
        seen.add(i)
        d = e.get("date") or "TBD"
        (up if d == "TBD" or d >= today else past).append(e)
    up.sort(key=lambda e: (e.get("date") in (None, "", "TBD"), e.get("date") or ""))
    past.sort(key=lambda e: e.get("date") or "", reverse=True)
    return up, past


def month_label(d):
    m = re.match(r"(\d{4})-(\d{2})", d or "")
    return f"{MOIS[int(m.group(2)) - 1].capitalize()} {m.group(1)}" if m else "Date à confirmer"


def day_label(d):
    m = re.match(r"\d{4}-(\d{2})-(\d{2})", d or "")
    return f"{int(m.group(2))} {COURT[int(m.group(1)) - 1]}" if m else "TBD"


def li(e):
    return (f'<li><a href="/sorties/{e["id"]}.html">{escape(clean_title(e.get("title")) or e["id"])}</a>'
            f' <span class="seo-d">{day_label(e.get("date"))}</span></li>')


def grouped(items):
    out, cur = [], None
    for e in items:
        m = month_label(e.get("date"))
        if m != cur:
            if cur is not None:
                out.append("</ul>")
            out.append(f"<h3>{m}</h3><ul>")
            cur = m
        out.append(li(e))
    if cur is not None:
        out.append("</ul>")
    return "".join(out)


CSS = ("<style>.seo-links{max-width:1200px;margin:2.5rem auto;padding:0 1rem;font-family:var(--font-body,'Barlow',sans-serif)}"
       ".seo-links h2{font-family:var(--font-display,'Bebas Neue',sans-serif);font-size:1.6rem;letter-spacing:.03em;margin:0 0 .8rem;color:var(--text,#0A0A0A)}"
       ".seo-links h2 span{color:var(--accent,#FF2D2D)}"
       ".seo-links h3{font-family:var(--font-cond,'Barlow Condensed',sans-serif);font-size:.95rem;text-transform:uppercase;letter-spacing:.06em;margin:1.2rem 0 .4rem;color:var(--muted,#666)}"
       ".seo-links ul{list-style:none;margin:0;padding:0;columns:3 260px;column-gap:2rem}"
       ".seo-links li{break-inside:avoid;padding:.18rem 0;font-size:.9rem;line-height:1.35}"
       ".seo-links a{color:var(--text,#0A0A0A);text-decoration:none}.seo-links a:hover{color:var(--accent,#FF2D2D);text-decoration:underline}"
       ".seo-links .seo-d{color:var(--muted,#888);font-size:.8rem;white-space:nowrap}"
       ".seo-links .seo-all{display:inline-block;margin-top:1rem;font-family:var(--font-cond,'Barlow Condensed',sans-serif);font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--accent,#FF2D2D)}</style>")


def block(title_html, body):
    return (f'{START}\n{CSS}<section class="seo-links" aria-label="Liste des sorties">'
            f'<h2>{title_html}</h2>{body}'
            f'<a class="seo-all" href="/{ARCHIVE}">Voir toutes les sorties →</a></section>\n{END}')


def inject(path, html_block, anchors):
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        print(f"  {path} absent, ignoré"); return
    s = open(p, encoding="utf-8").read()
    s = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", s, flags=re.S)
    for a in anchors:
        if a in s:
            s = s.replace(a, html_block + "\n" + a, 1)
            open(p, "w", encoding="utf-8").write(s)
            print(f"  {path} : liens ajoutés")
            return
    print(f"  {path} : ancre introuvable, ignoré")


def archive_page(up, past):
    n = len(up) + len(past)
    desc = (f"Calendrier complet des sorties sneakers en France : {len(up)} sorties à venir et "
            f"{len(past)} sorties passées (Nike, Jordan, Adidas, New Balance...), avec dates, prix et liens retailers.")
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Toutes les sorties sneakers — calendrier complet | SneakerDropFR</title>
<meta name="description" content="{escape(desc, quote=True)}">
<link rel="canonical" href="{SITE}/{ARCHIVE}">
<meta property="og:title" content="Toutes les sorties sneakers | SneakerDropFR">
<meta property="og:description" content="{escape(desc, quote=True)}">
<meta property="og:url" content="{SITE}/{ARCHIVE}">
<meta property="og:type" content="website">
<link rel="icon" href="/favicon.ico">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:wght@400;600&family=Barlow+Condensed:wght@600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#FFFFFF;--text:#0A0A0A;--accent:#FF2D2D;--muted:#666;--border:#E5E5E5;--bg-alt:#F5F5F5;
--font-display:'Bebas Neue',sans-serif;--font-body:'Barlow',sans-serif;--font-cond:'Barlow Condensed',sans-serif}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:var(--font-body)}}
header{{border-bottom:1px solid var(--border);padding:1rem}}
header .in{{max-width:1200px;margin:0 auto;display:flex;gap:1.5rem;align-items:center;flex-wrap:wrap}}
header a{{color:var(--text);text-decoration:none;font-family:var(--font-cond);font-weight:700;text-transform:uppercase;letter-spacing:.05em;font-size:.9rem}}
header .logo{{font-family:var(--font-display);font-size:1.6rem;letter-spacing:.03em}}
header .logo span{{color:var(--accent)}}
h1{{font-family:var(--font-display);font-size:2.6rem;letter-spacing:.03em;max-width:1200px;margin:2rem auto .3rem;padding:0 1rem}}
h1 span{{color:var(--accent)}}
.intro{{max-width:1200px;margin:0 auto;padding:0 1rem;color:var(--muted)}}
footer{{text-align:center;padding:2rem;font-family:var(--font-cond);font-size:.8rem;color:var(--muted);border-top:1px solid var(--border);margin-top:3rem}}
footer a{{color:var(--muted)}}
</style>
</head>
<body>
<header><div class="in">
<a class="logo" href="/">SneakerDrop<span>FR</span></a>
<a href="/sorties.html">Sorties</a><a href="/restocks.html">Restocks</a><a href="/deals.html">Deals</a><a href="/raffles.html">Raffles</a>
<a href="/categories/nike.html">Nike</a><a href="/categories/jordan.html">Jordan</a><a href="/categories/adidas.html">Adidas</a><a href="/categories/new-balance.html">New Balance</a>
</div></header>
<h1>Toutes les <span>sorties</span> sneakers</h1>
<p class="intro">{n} paires : les {len(up)} prochaines sorties, puis les {len(past)} sorties passées, mois par mois.</p>
{CSS}
<section class="seo-links"><h2>Sorties <span>à venir</span></h2>{grouped(up)}</section>
<section class="seo-links"><h2>Sorties <span>passées</span></h2>{grouped(past)}</section>
<footer>© {date.today().year} SneakerDrop FR — <a href="/">Accueil</a> · <a href="/mentions-legales.html">Mentions légales</a> · <a href="/privacy.html">Confidentialité</a></footer>
</body>
</html>
"""


def add_to_sitemap():
    p = os.path.join(ROOT, "sitemap.xml")
    if not os.path.exists(p):
        return
    s = open(p, encoding="utf-8").read()
    url = f"{SITE}/{ARCHIVE}"
    if url in s or "</urlset>" not in s:
        return
    entry = (f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{date.today().isoformat()}</lastmod>\n"
             f"    <changefreq>daily</changefreq>\n    <priority>0.8</priority>\n  </url>\n")
    open(p, "w", encoding="utf-8").write(s.replace("</urlset>", entry + "</urlset>", 1))
    print("  sitemap.xml : toutes-les-sorties.html ajoutée")


def main():
    up, past = collect()
    print(f"SEO links : {len(up)} à venir, {len(past)} passées (fiches existantes)")
    if not up and not past:
        print("  aucune fiche, rien à faire"); return
    open(os.path.join(ROOT, ARCHIVE), "w", encoding="utf-8").write(archive_page(up, past))
    print(f"  {ARCHIVE} : {len(up) + len(past)} liens")
    dated = [e for e in up if re.match(r"\d{4}-\d{2}-\d{2}$", e.get("date") or "")]
    home = block("Prochaines <span>sorties</span>", grouped(dated[:60]))
    inject("index.html", home, ['<footer class="footer">', "</body>"])
    inject("sorties.html", home, ['<footer class="footer">', "</body>"])
    for slug, f in CATS.items():
        cu = [e for e in dated if f(e)]
        cp = [e for e in past if f(e)][:80]
        body = ""
        if cu:
            body += grouped(cu)
        if cp:
            body += '<h2 style="margin-top:2rem">Dernières <span>sorties</span></h2>' + grouped(cp)
        if body:
            inject(f"categories/{slug}.html",
                   block(f"Sorties <span>{CAT_NAMES[slug]}</span>", body), ["<footer", "</body>"])
    add_to_sitemap()


if __name__ == "__main__":
    main()
