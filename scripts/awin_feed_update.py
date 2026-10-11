#!/usr/bin/env python3
"""Télécharge le flux produits Awin (Snipes, Solebox, Reebok…) et remplace le fichier local seulement s'il est valide.
L'adresse du flux (avec la clé API) est lue dans /root/.awin_feed_url — jamais affichée."""
import os, sys, gzip, csv, io, urllib.request, collections, time
URL_FILE = os.environ.get("AWIN_URL_FILE", "/root/.awin_feed_url")
DEST = os.environ.get("AWIN_FEED_DEST", "/root/awin_feed_snipes_solebox.csv.gz")
NEEDED = {"aw_deep_link", "product_name", "merchant_name", "merchant_deep_link", "merchant_image_url",
          "search_price", "merchant_category", "in_stock"}
MIN_ROWS = 1000
def log(m): print(time.strftime("%Y-%m-%d %H:%M"), "[awin_feed]", m, flush=True)
try:
    url = open(URL_FILE, encoding="utf-8").read().strip()
except FileNotFoundError:
    log("adresse du flux absente (%s) — rien fait" % URL_FILE); sys.exit(1)
if not url.startswith("http"):
    log("adresse du flux invalide dans %s — rien fait" % URL_FILE); sys.exit(1)
tmp = DEST + ".tmp"
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b: break
            f.write(b)
    with gzip.open(tmp, "rt", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        miss = NEEDED - set(rd.fieldnames or [])
        if miss: raise ValueError("colonnes manquantes : " + ", ".join(sorted(miss)))
        n = 0; shops = collections.Counter()
        for row in rd:
            n += 1; shops[row.get("merchant_name", "?")] += 1
    if n < MIN_ROWS: raise ValueError("seulement %d lignes" % n)
    os.replace(tmp, DEST)
    log("OK — %d lignes : %s" % (n, ", ".join("%s %d" % kv for kv in shops.most_common())))
except Exception as e:
    try: os.remove(tmp)
    except OSError: pass
    log("ÉCHEC (%s) — ancien flux conservé" % str(e)[:150]); sys.exit(1)
