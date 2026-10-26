#!/usr/bin/env python3
"""deals_affilies.py : bannière Solebox Flash Sale -25 % (sans code), 26/10 → 02/11/2026."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "du 26/10 au 02/11" in s:
    print("Déjà patché."); sys.exit(0)
ENTRY = '''PROMOS = [
    {"code": "", "text": "FLASH SALE SOLEBOX", "label": "-25% sur une sélection, du 26/10 au 02/11",
     "url": "https://www.awin1.com/cread.php?awinmid=20964&awinaffid=2855487&ued=https%3A%2F%2Fwww.solebox.com%2Ffr-fr%2Fc%2F4171",
     "start": "2026-10-26", "end": "2026-11-02"},
'''
if s.count("PROMOS = [\n") != 1:
    sys.exit("Ancre PROMOS introuvable — rien modifié")
shutil.copy(P, P + ".bak_solebox_flash")
open(P, "w", encoding="utf-8").write(s.replace("PROMOS = [\n", ENTRY, 1))
print("OK — bannière Flash Sale Solebox ajoutée du 26/10 au 02/11 (sauvegarde " + P + ".bak_solebox_flash)")
