#!/usr/bin/env python3
"""deals_affilies.py : bannière SNIPES WEEKEND DEAL (jusqu'à -20 %, 23/10 20h → 26/10 10h, sans code promo)."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "SNIPES WEEKEND DEAL" in s:
    print("Déjà patché."); sys.exit(0)
ENTRY = '''PROMOS = [
    {"code": "", "text": "SNIPES WEEKEND DEAL", "label": "jusqu'à -20% sur une sélection, du 23 au 26/10",
     "url": "https://www.awin1.com/cread.php?awinmid=122628&awinaffid=2855487&ued=https%3A%2F%2Fwww.snipes.com%2Ffr-fr%2Fc%2Fsale-660",
     "start": "2026-10-23", "end": "2026-10-26"},
'''
if s.count("PROMOS = [\n") != 1:
    sys.exit("Ancre PROMOS introuvable — rien modifié")
shutil.copy(P, P + ".bak_promo_weekend")
open(P, "w", encoding="utf-8").write(s.replace("PROMOS = [\n", ENTRY, 1))
print("OK — bannière SNIPES WEEKEND DEAL ajoutée du 23 au 26/10 (sauvegarde " + P + ".bak_promo_weekend)")
