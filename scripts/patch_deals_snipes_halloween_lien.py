#!/usr/bin/env python3
"""deals_affilies.py : bannière Snipes Halloween → lien vers la page deals Snipes FR (la page Halloween FR est en 404)."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
OLD = "https%3A%2F%2Fwww.snipes.com%2Ffr-fr%2Fc%2Fdeals-halloween-1351"
NEW = "https%3A%2F%2Fwww.snipes.com%2Ffr-fr%2Fc%2Fdeals-1205"
s = open(P, encoding="utf-8").read()
if OLD not in s:
    print("Déjà patché ou bannière absente — rien modifié."); sys.exit(0)
shutil.copy(P, P + ".bak_snipes_halloween_lien")
open(P, "w", encoding="utf-8").write(s.replace(OLD, NEW))
print("OK — lien Halloween Snipes remplacé par la page deals FR (sauvegarde " + P + ".bak_snipes_halloween_lien)")
