#!/usr/bin/env python3
"""deals_affilies.py : bannières BSTN Singles Week SINGLE20 (-20 %, 09/11 → 15/11) et Singles Day SINGLE25 (-25 %, 11/11)."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "SINGLE20" in s:
    print("Déjà patché."); sys.exit(0)
ENTRY = """PROMOS = [
    {"code": "SINGLE25", "text": "SINGLES DAY BSTN", "label": "-25% sur tout, le 11/11",
     "url": "https://www.awin1.com/cread.php?awinmid=104979&awinaffid=2855487&ued=https%3A%2F%2Fwww.bstn.com%2Feu_fr%2Fmen%2Fall-products%3Fcategories%3DMen~All%2520Products%26bstn_collection%3DCODE%253A%2520SINGLE25",
     "start": "2026-11-11", "end": "2026-11-11"},
    {"code": "SINGLE20", "text": "SINGLES WEEK BSTN", "label": "-20% sur tout, du 09/11 au 15/11",
     "url": "https://www.awin1.com/cread.php?awinmid=104979&awinaffid=2855487&ued=https%3A%2F%2Fwww.bstn.com%2Feu_fr%2Fmen%2Fall-products%3Fcategories%3DMen~All%2520Products%26bstn_collection%3DCODE%253A%2520SINGLE20",
     "start": "2026-11-09", "end": "2026-11-15"},
"""
if s.count("PROMOS = [\n") != 1:
    sys.exit("Ancre PROMOS introuvable — rien modifié")
shutil.copy(P, P + ".bak_single20")
open(P, "w", encoding="utf-8").write(s.replace("PROMOS = [\n", ENTRY, 1))
print("OK — bannières SINGLE20 (09/11–15/11) et SINGLE25 (11/11) ajoutées (sauvegarde " + P + ".bak_single20)")
