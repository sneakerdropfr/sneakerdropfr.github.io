#!/usr/bin/env python3
"""deals_affilies.py : onglet « BSTN Catalogue » renommé « BSTN » et limité aux sneakers adultes
(catégorie Awin « Men/Women > Footwear > Sneakers ») — plus de vêtements, enfants, claquettes."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "BSTN_CAT_OK" in s:
    print("Déjà patché."); sys.exit(0)
A1 = "            if bn.lower() not in BSTN_BRANDS: continue\n"
B1 = A1 + ("            _cp = (r.get('merchant_product_category_path', '') or '').strip()\n"
           "            if _cp and not BSTN_CAT_OK.match(_cp): continue\n")
A2 = "def load_bstn_catalog("
B2 = "BSTN_CAT_OK = re.compile(r'^(Men|Women) > Footwear > Sneakers$')\n" + A2
A3 = ">BSTN Catalogue</button>"
B3 = ">BSTN</button>"
for a in (A1, A2, A3):
    if s.count(a) != 1:
        sys.exit("Ancre introuvable ou multiple — rien modifié : " + a.strip()[:60])
s = s.replace(A2, B2, 1).replace(A1, B1, 1).replace(A3, B3, 1)
shutil.copy(P, P + ".bak_bstnsneakers")
open(P, "w", encoding="utf-8").write(s)
print("OK — onglet BSTN : sneakers uniquement (sauvegarde %s.bak_bstnsneakers)" % P)
import re, gzip, csv, os
m = re.search(r'FEED_PATH\s*=\s*["\']([^"\']+)', s)
fp = m.group(1) if m else ""
if fp and os.path.exists(fp):
    with gzip.open(fp, "rt", encoding="utf-8", newline="") as f:
        cols = csv.DictReader(f).fieldnames or []
    print("Flux : colonne catégorie présente" if "merchant_product_category_path" in cols
          else "ATTENTION : colonne merchant_product_category_path absente du flux — filtre inactif")
