#!/usr/bin/env python3
"""deals_affilies.py : lien de la bannière Singles' Day Reebok basculé vers reebok.eu/fr-fr (page collection en 404)."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
OLD = "ued=https%3A%2F%2Fwww.reebok.eu%2Ffr-fr%2Fcollections%2Fsingles-day"
NEW = "ued=https%3A%2F%2Fwww.reebok.eu%2Ffr-fr"
if OLD not in s:
    print("Déjà patché." if "SINGLES' DAY REEBOK" in s else "Bannière Reebok introuvable — rien modifié"); sys.exit(0)
if s.count(OLD) != 1:
    sys.exit("Lien présent plusieurs fois — rien modifié")
shutil.copy(P, P + ".bak_reebok_lien")
open(P, "w", encoding="utf-8").write(s.replace(OLD, NEW, 1))
print("OK — lien Singles' Day Reebok → reebok.eu/fr-fr (sauvegarde %s.bak_reebok_lien)" % P)
