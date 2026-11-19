#!/usr/bin/env python3
"""health_check.py : ne surveille plus sneaker-daily-drops (désactivé, remplacé par bstn_feed.py « SORTIE DU JOUR »)."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/health_check.py"
s = open(P, encoding="utf-8").read()
OLD = '    all_problems += check_systemd_timer("sneaker-daily-drops.service", 26, "daily_drops.py (1x/jour 6h00 via systemd)")\n'
NEW = '    # désactivé : remplacé par bstn_feed.py (SORTIE DU JOUR)\n    # all_problems += check_systemd_timer("sneaker-daily-drops.service", 26, "daily_drops.py (1x/jour 6h00 via systemd)")\n'
if NEW in s:
    print("Déjà patché."); sys.exit(0)
if s.count(OLD) != 1:
    sys.exit("Ligne sneaker-daily-drops introuvable — rien modifié")
shutil.copy(P, P + ".bak_dailydrops")
open(P, "w", encoding="utf-8").write(s.replace(OLD, NEW, 1))
import py_compile; py_compile.compile(P, doraise=True)
print("OK — daily_drops retiré de la surveillance (sauvegarde %s.bak_dailydrops)" % P)
