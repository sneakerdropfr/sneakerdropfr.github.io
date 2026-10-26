#!/usr/bin/env python3
"""deals_affilies.py : bannière BSTN Halloween Sale, code GHOST20 (-20 %), 26/10 → 01/11/2026."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "GHOST20" in s:
    print("Déjà patché."); sys.exit(0)
ENTRY = '''PROMOS = [
    {"code": "GHOST20", "text": "HALLOWEEN SALE BSTN", "label": "-20% du 26/10 au 01/11",
     "url": "https://www.awin1.com/cread.php?awinmid=104979&awinaffid=2855487&ued=https%3A%2F%2Fwww.bstn.com%2Feu_fr%2F",
     "start": "2026-10-26", "end": "2026-11-01"},
'''
if s.count("PROMOS = [\n") != 1:
    sys.exit("Ancre PROMOS introuvable — rien modifié")
shutil.copy(P, P + ".bak_ghost20")
open(P, "w", encoding="utf-8").write(s.replace("PROMOS = [\n", ENTRY, 1))
print("OK — bannière GHOST20 ajoutée du 26/10 au 01/11 (sauvegarde " + P + ".bak_ghost20)")
