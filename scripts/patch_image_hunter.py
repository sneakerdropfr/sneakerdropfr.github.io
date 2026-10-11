#!/usr/bin/env python3
"""Fait écrire un rapport vide à image_hunter.py quand aucune image ne manque."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/image_hunter.py"
L = open(P, encoding="utf-8").read().split(chr(10))
if any("_ih_empty_report" in l for l in L):
    print("Déjà patché."); sys.exit(0)
idx = [i for i, l in enumerate(L) if "Aucune image manquante" in l]
if len(idx) != 1:
    sys.exit("Ligne 'Aucune image manquante' introuvable ou multiple — rien modifié")
i = idx[0]
if not L[i].lstrip().startswith("print"):
    sys.exit("Ligne inattendue — rien modifié : " + L[i])
ind = L[i][:len(L[i]) - len(L[i].lstrip())]
L.insert(i, ind + 'import json as _j, time as _t; _j.dump({"generated_at": _t.strftime("%Y-%m-%d %H:%M"), "total_missing": 0, "priority": []}, open(REPORT_PATH, "w", encoding="utf-8"), ensure_ascii=False)  # _ih_empty_report')
shutil.copy(P, P + ".bak2")
open(P, "w", encoding="utf-8").write(chr(10).join(L))
print("OK — rapport vide écrit quand rien ne manque (ligne %d, sauvegarde %s.bak2)" % (i + 1, P))
