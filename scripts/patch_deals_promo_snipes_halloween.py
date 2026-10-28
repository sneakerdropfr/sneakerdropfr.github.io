#!/usr/bin/env python3
"""deals_affilies.py : bannière Snipes Halloween Deal -20 % (membres Snipes Club), 29/10 → 02/11/2026."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "HALLOWEEN DEAL SNIPES" in s:
    print("Déjà patché."); sys.exit(0)
ENTRY = '''PROMOS = [
    {"code": "", "text": "HALLOWEEN DEAL SNIPES", "label": "-20% sur tout pour les membres Snipes Club, du 29/10 au 02/11",
     "url": "https://www.awin1.com/cread.php?awinmid=122628&awinaffid=2855487&ued=https%3A%2F%2Fwww.snipes.com%2Ffr-fr%2Fc%2Fdeals-halloween-1351",
     "start": "2026-10-29", "end": "2026-11-02"},
'''
if s.count("PROMOS = [\n") != 1:
    sys.exit("Ancre PROMOS introuvable — rien modifié")
shutil.copy(P, P + ".bak_snipes_halloween")
open(P, "w", encoding="utf-8").write(s.replace("PROMOS = [\n", ENTRY, 1))
print("OK — bannière Halloween Deal Snipes ajoutée du 29/10 au 02/11 (sauvegarde " + P + ".bak_snipes_halloween)")
