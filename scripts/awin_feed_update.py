#!/usr/bin/env python3
"""Télécharge un ou plusieurs flux produits Awin et les fusionne dans un seul fichier.
- Adresses (avec la clé API) lues dans /root/.awin_feed_url, une par ligne — jamais affichées.
- Chaque flux valide est gardé en cache ; si un flux échoue, sa dernière bonne version est réutilisée.
- Le fichier final n'est remplacé que si la fusion est valide."""
import os, sys, gzip, csv, urllib.request, collections, time, hashlib, shutil
csv.field_size_limit(10**8)
URL_FILE = os.environ.get("AWIN_URL_FILE", "/root/.awin_feed_url")
DEST = os.environ.get("AWIN_FEED_DEST", "/root/awin_feed_snipes_solebox.csv.gz")
CACHE = os.environ.get("AWIN_CACHE_DIR", "/root/awin_feeds")
NEEDED = {"aw_deep_link", "product_name", "merchant_name", "merchant_deep_link", "merchant_image_url",
          "search_price", "merchant_category", "in_stock"}
MIN_ROWS_FEED, MIN_ROWS_TOTAL = 100, 1000
def log(m): print(time.strftime("%Y-%m-%d %H:%M"), "[awin_feed]", m, flush=True)

def check(path):
    """Renvoie (lignes, Counter des enseignes) ou lève une erreur si le flux est invalide."""
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        miss = NEEDED - set(rd.fieldnames or [])
        if miss: raise ValueError("colonnes manquantes : " + ", ".join(sorted(miss)))
        shops = collections.Counter(r.get("merchant_name", "?") for r in rd)
    n = sum(shops.values())
    if n < MIN_ROWS_FEED: raise ValueError("seulement %d lignes" % n)
    return n, shops

def desc(shops): return ", ".join("%s %d" % kv for kv in shops.most_common())

try:
    urls = [l.strip() for l in open(URL_FILE, encoding="utf-8") if l.strip() and not l.strip().startswith("#")]
except FileNotFoundError:
    log("fichier d'adresses absent (%s) — rien fait" % URL_FILE); sys.exit(1)
if not urls or not all(u.startswith("http") for u in urls):
    log("adresse(s) invalide(s) dans %s — rien fait" % URL_FILE); sys.exit(1)
os.makedirs(CACHE, exist_ok=True)

usable, fresh, stale, missing = [], 0, 0, 0
for i, url in enumerate(urls, 1):
    cache = os.path.join(CACHE, "flux_%s.csv.gz" % hashlib.sha256(url.encode()).hexdigest()[:12])
    tmp = cache + ".tmp"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 20)
        n, shops = check(tmp)
        os.replace(tmp, cache); fresh += 1; usable.append(cache)
        log("flux %d : OK — %d lignes (%s)" % (i, n, desc(shops)))
    except Exception as e:
        try: os.remove(tmp)
        except OSError: pass
        if os.path.exists(cache):
            age = (time.time() - os.path.getmtime(cache)) / 3600
            stale += 1; usable.append(cache)
            log("flux %d : ÉCHEC (%s) — dernière bonne version réutilisée (%.0f h)" % (i, str(e)[:120], age))
        else:
            missing += 1
            log("flux %d : ÉCHEC (%s) — aucune version en cache, flux ignoré" % (i, str(e)[:120]))

if not usable:
    log("ÉCHEC — aucun flux utilisable, ancien fichier conservé"); sys.exit(1)
out_tmp = DEST + ".tmp"
try:
    cols = []
    for p in usable:
        with gzip.open(p, "rt", encoding="utf-8", newline="") as f:
            for c in csv.DictReader(f).fieldnames:
                if c not in cols: cols.append(c)
    n = 0; shops = collections.Counter()
    with gzip.open(out_tmp, "wt", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=cols, extrasaction="ignore"); w.writeheader()
        for p in usable:
            with gzip.open(p, "rt", encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    w.writerow(row); n += 1; shops[row.get("merchant_name", "?")] += 1
    if n < MIN_ROWS_TOTAL: raise ValueError("seulement %d lignes au total" % n)
    os.replace(out_tmp, DEST)
except Exception as e:
    try: os.remove(out_tmp)
    except OSError: pass
    log("ÉCHEC fusion (%s) — ancien fichier conservé" % str(e)[:150]); sys.exit(1)
log("OK — %d flux (%d à jour, %d en cache, %d ignoré(s)), %d lignes : %s" % (len(urls), fresh, stale, missing, n, desc(shops)))
