#!/usr/bin/env python3
"""deals_affilies.py : affinage du catalogue BSTN — abréviations vêtements/enfants (T-Shirt collé, TEE, SS CRW, JDB/NKB…),
Crocs retiré, sélection par plus forte remise puis le reste (au lieu des moins chères)."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "BSTN_EXCL2" in s:
    print("Déjà patché."); sys.exit(0)
if "def load_bstn_catalog(" not in s:
    sys.exit("Le patch BSTN Catalogue doit être appliqué avant — rien modifié")
EX2 = r'''BSTN_EXCL2 = re.compile(r'shirt|short|shor$|hood|coverall|ballcap|pack|pck|waist|jibbitz|charm|sweat|jersey|legging|trouser|fleece|sock|'
    r'tee(?=\W|$)|(?<!\w)(?:ss|crw|po|set|flc|jdb|nkb|nab|nsw|tank|\d+ ?in|k|t|boys|girls)(?=\W|$)', re.IGNORECASE)
'''
R = [
 ("'timberland','ugg','birkenstock','crocs','clarks']", "'timberland','ugg','birkenstock','clarks']"),
 ("def load_bstn_catalog(", EX2 + "def load_bstn_catalog("),
 ("            if not nm or BSTN_EXCL.search(nm): continue", "            if not nm or BSTN_EXCL.search(nm) or BSTN_EXCL2.search(nm): continue"),
 ("'_promo': old > p}", "'_promo': old > p, '_disc': ((old - p) / old if old > p else 0)}"),
 ("    out.sort(key=lambda x: (not x['_promo'], x['price']))", "    out.sort(key=lambda x: -x['_disc'])"),
 ("    for x in out: x.pop('_promo', None)", "    for x in out: x.pop('_promo', None); x.pop('_disc', None)"),
]
for a, b in R:
    if s.count(a) != 1:
        sys.exit("Ancre introuvable ou multiple — rien modifié : " + a.strip()[:60])
for a, b in R:
    s = s.replace(a, b, 1)
shutil.copy(P, P + ".bak_bstncat2")
open(P, "w", encoding="utf-8").write(s)
print("OK — catalogue BSTN affiné (sauvegarde %s.bak_bstncat2)" % P)
