#!/usr/bin/env python3
"""deals_affilies.py : bannière Solebox EXTRA20 (-20 % en plus sur les soldes), 20 → 23/10/2026."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "EXTRA20" in s:
    print("Déjà patché."); sys.exit(0)
ENTRY = '''PROMOS = [
    {"code": "EXTRA20", "text": "SOLDES SOLEBOX", "label": "-20% en plus du 20 au 23/10",
     "url": "https://www.awin1.com/cread.php?awinmid=20964&awinaffid=2855487&ued=https%3A%2F%2Fwww.solebox.com%2Ffr-fr%2Fc%2Fsale-2775",
     "start": "2026-10-20", "end": "2026-10-23"},
'''
if s.count("PROMOS = [\n") != 1:
    sys.exit("Ancre PROMOS introuvable — rien modifié")
shutil.copy(P, P + ".bak_extra20")
open(P, "w", encoding="utf-8").write(s.replace("PROMOS = [\n", ENTRY, 1))
print("OK — bannière EXTRA20 ajoutée du 20 au 23/10 (sauvegarde %s.bak_extra20)" % P)
