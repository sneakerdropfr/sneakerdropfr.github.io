#!/usr/bin/env python3
"""Télécharge un ou plusieurs flux produits Awin, les fusionne et remplace le fichier local seulement si tout est valide.
Adresses (avec la clé API) lues dans /root/.awin_feed_url, une par ligne — jamais affichées."""
import os, sys, gzip, csv, urllib.request, collections, time
csv.field_size_limit(10**8)
URL_FILE = os.environ.get("AWIN_URL_FILE", "/root/.awin_feed_url")
DEST = os.environ.get("AWIN_FEED_DEST", "/root/awin_feed_snipes_solebox.csv.gz")
NEEDED = {"aw_deep_link", "product_name", "merchant_name", "merchant_deep_link", "merchant_image_url",
          "search_price", "merchant_category", "in_stock"}
MIN_ROWS = 1000
def log(m): print(time.strftime("%Y-%m-%d %H:%M"), "[awin_feed]", m, flush=True)
try:
    urls = [l.strip() for l in open(URL_FILE, encoding="utf-8") if l.strip() and not l.strip().startswith("#")]
except FileNotFoundError:
    log("fichier d'adresses absent (%s) — rien fait" % URL_FILE); sys.exit(1)
if not urls or not all(u.startswith("http") for u in urls):
    log("adresse(s) invalide(s) dans %s — rien fait" % URL_FILE); sys.exit(1)
parts, tmp = [], DEST + ".tmp"
try:
    for i, url in enumerate(urls, 1):
        p = "%s.part%d" % (DEST, i); parts.append(p)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=300) as r, open(p, "wb") as f:
            while True:
                b = r.read(1 << 20)
                if not b: break
                f.write(b)
        with gzip.open(p, "rt", encoding="utf-8", newline="") as f:
            fn = csv.DictReader(f).fieldnames or []
        miss = NEEDED - set(fn)
        if miss: raise ValueError("flux %d : colonnes manquantes : %s" % (i, ", ".join(sorted(miss))))
    cols = []
    for p in parts:
        with gzip.open(p, "rt", encoding="utf-8", newline="") as f:
            for c in csv.DictReader(f).fieldnames:
                if c not in cols: cols.append(c)
    n = 0; shops = collections.Counter()
    with gzip.open(tmp, "wt", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for p in parts:
            with gzip.open(p, "rt", encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    w.writerow(row); n += 1; shops[row.get("merchant_name", "?")] += 1
    if n < MIN_ROWS: raise ValueError("seulement %d lignes" % n)
    os.replace(tmp, DEST)
    log("OK — %d flux, %d lignes : %s" % (len(urls), n, ", ".join("%s %d" % kv for kv in shops.most_common())))
    rc = 0
except Exception as e:
    log("ÉCHEC (%s) — ancien flux conservé" % str(e)[:150]); rc = 1
finally:
    for p in parts + [tmp]:
        try: os.remove(p)
        except OSError: pass
sys.exit(rc)
