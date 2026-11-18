#!/usr/bin/env python3
"""deals_affilies.py : bannières BSTN Black Week BLACK25 (-25 %, 20/11 → 30/11) et WINTER20 (-20 % vêtements d'hiver, 16/11 → 19/11)."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "BLACK25" in s:
    print("Déjà patché."); sys.exit(0)
ENTRY = """PROMOS = [
    {"code": "BLACK25", "text": "BLACK WEEK BSTN", "label": "-25% du 20/11 au 30/11",
     "url": "https://www.awin1.com/cread.php?awinmid=104979&awinaffid=2855487&ued=https%3A%2F%2Fwww.bstn.com%2Feu_fr%2F",
     "start": "2026-11-20", "end": "2026-11-30"},
    {"code": "WINTER20", "text": "WINTER SALE BSTN", "label": "-20% sur les vêtements d'hiver, jusqu'au 19/11",
     "url": "https://www.awin1.com/cread.php?awinmid=104979&awinaffid=2855487&ued=https%3A%2F%2Fwww.bstn.com%2Feu_fr%2Fmen%2Fall-products%3Fcategories%3DMen~All%2520Products%26bstn_collection%3DCODE%253A%2520WINTER20",
     "start": "2026-11-16", "end": "2026-11-19"},
"""
if s.count("PROMOS = [\n") != 1:
    sys.exit("Ancre PROMOS introuvable — rien modifié")
shutil.copy(P, P + ".bak_black25")
open(P, "w", encoding="utf-8").write(s.replace("PROMOS = [\n", ENTRY, 1))
print("OK — bannières BLACK25 (20/11–30/11) et WINTER20 (16/11–19/11) ajoutées (sauvegarde " + P + ".bak_black25)")
