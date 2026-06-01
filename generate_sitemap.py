#!/usr/bin/env python3
"""
Génère automatiquement sitemap.xml depuis les fichiers .html du repo.
Exécuté par GitHub Actions à chaque push.
"""
import os, glob
from datetime import date

BASE_URL = "https://sneakerdropfr.fr"
TODAY = date.today().isoformat()

# Pages avec leur priorité et fréquence
PAGE_CONFIG = {
    "index.html":        {"priority": "1.0", "changefreq": "daily",   "path": "/"},
    "sorties.html":      {"priority": "0.9", "changefreq": "daily",   "path": "/sorties.html"},
    "raffles.html":      {"priority": "0.9", "changefreq": "daily",   "path": "/raffles.html"},
    "calendar.html":     {"priority": "0.9", "changefreq": "daily",   "path": "/calendar.html"},
    "hype-picks.html":   {"priority": "0.8", "changefreq": "weekly",  "path": "/hype-picks.html"},
    "deals.html":        {"priority": "0.7", "changefreq": "weekly",  "path": "/deals.html"},
    "bstn-deals.html":   {"priority": "0.7", "changefreq": "daily",   "path": "/bstn-deals.html"},
    "bstn-promos.html":  {"priority": "0.7", "changefreq": "daily",   "path": "/bstn-promos.html"},
    "privacy.html":      {"priority": "0.3", "changefreq": "monthly", "path": "/privacy.html"},
}

urls = []

# Pages principales configurées
for fname, cfg in PAGE_CONFIG.items():
    if os.path.exists(fname):
        urls.append({
            "loc": BASE_URL + cfg["path"],
            "lastmod": TODAY,
            "changefreq": cfg["changefreq"],
            "priority": cfg["priority"]
        })

# Pages blog/
for fpath in sorted(glob.glob("blog/*.html")):
    slug = os.path.basename(fpath).replace(".html", "")
    urls.append({
        "loc": f"{BASE_URL}/blog/{slug}.html",
        "lastmod": TODAY,
        "changefreq": "monthly",
        "priority": "0.6"
    })

# Pages sorties/ individuelles
for fpath in sorted(glob.glob("sorties/*.html")):
    fname = os.path.basename(fpath)
    slug = fname.replace(".html", "")
    urls.append({
        "loc": f"{BASE_URL}/sorties/{slug}.html",
        "lastmod": TODAY,
        "changefreq": "monthly",
        "priority": "0.6"
    })

# Générer le XML
lines = ['''<?xml version="1.0" encoding="UTF-8"?>''',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

for u in urls:
    lines.append(f'''  <url>
    <loc>{u["loc"]}</loc>
    <lastmod>{u["lastmod"]}</lastmod>
    <changefreq>{u["changefreq"]}</changefreq>
    <priority>{u["priority"]}</priority>
  </url>''')

lines.append('</urlset>')

sitemap = "\n".join(lines) + "\n"

with open("sitemap.xml", "w", encoding="utf-8") as f:
    f.write(sitemap)

print(f"sitemap.xml généré — {len(urls)} URLs")
