#!/usr/bin/env python3
"""deals_affilies.py : bannière BSTN Premium Sale, code PRM25 (-25 %), 17 → 18/10/2026."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "PRM25" in s:
    print("Déjà patché."); sys.exit(0)
ENTRY = '''PROMOS = [
    {"code": "PRM25", "text": "PREMIUM SALE BSTN", "label": "-25% les 17 & 18/10",
     "url": "https://www.awin1.com/cread.php?awinmid=104979&awinaffid=2855487&ued=https%3A%2F%2Fwww.bstn.com%2Feu_fr%2F",
     "start": "2026-10-17", "end": "2026-10-18"},
'''
if s.count("PROMOS = [\n") != 1:
    sys.exit("Ancre PROMOS introuvable — rien modifié")
shutil.copy(P, P + ".bak_prm25")
open(P, "w", encoding="utf-8").write(s.replace("PROMOS = [\n", ENTRY, 1))
print("OK — bannière PRM25 ajoutée pour les 17 et 18/10 (sauvegarde %s.bak_prm25)" % P)
