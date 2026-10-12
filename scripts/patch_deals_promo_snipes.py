#!/usr/bin/env python3
"""deals_affilies.py : bannière SNIPES FLASH DEAL (jusqu'à -30 %, 12/10 → 29/10/2026, sans code promo)."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "SNIPES FLASH DEAL" in s:
    print("Déjà patché."); sys.exit(0)
ENTRY = '''PROMOS = [
    {"code": "", "text": "SNIPES FLASH DEAL", "label": "jusqu'à -30% sur une sélection, jusqu'au 29/10",
     "url": "https://www.awin1.com/cread.php?awinmid=122628&awinaffid=2855487&ued=https%3A%2F%2Fwww.snipes.com%2Ffr-fr%2Fc%2Fdeals-flash-deal-1205",
     "start": "2026-10-12", "end": "2026-10-29"},
'''
END = '''Voir les offres →</a></div>')\n'''
FIX = END + '''        if not p["code"]: out[-1] = re.sub(r'<span[^>]*clipboard[^>]*></span> = ', '', out[-1])  # promo sans code\n'''
for a in ["PROMOS = [\n", END]:
    if s.count(a) != 1:
        sys.exit("Ancre introuvable ou multiple — rien modifié : " + a.strip()[:50])
s = s.replace("PROMOS = [\n", ENTRY, 1).replace(END, FIX, 1)
shutil.copy(P, P + ".bak_promo_snipes")
open(P, "w", encoding="utf-8").write(s)
print("OK — bannière SNIPES FLASH DEAL ajoutée jusqu'au 29/10 (sauvegarde %s.bak_promo_snipes)" % P)
