#!/usr/bin/env python3
"""health_check.py : retire merge-perplexity.sh (désactivé) de la surveillance et surveille à la place
les tâches quotidiennes de 7h30 (flux Awin + page deals)."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/health_check.py"
s = open(P, encoding="utf-8").read()
OLD = '    ("/var/log/merge-perplexity.log", 30, "merge-perplexity.sh (1x/jour 3h00)"),\n'
NEW = ('    # ("/var/log/merge-perplexity.log", 30, "merge-perplexity.sh (1x/jour 3h00)"),  # désactivé dans le crontab\n'
       '    ("/var/log/awin_feed.log", 30, "awin_feed_update.py (1x/jour 7h30)"),\n'
       '    ("/var/log/run_deals.log", 30, "run_deals.sh — page deals (1x/jour 7h30)"),\n')
if "awin_feed.log" in s:
    print("Déjà patché."); sys.exit(0)
if s.count(OLD) != 1:
    sys.exit("Ligne merge-perplexity introuvable — rien modifié")
shutil.copy(P, P + ".bak_cronlogs")
open(P, "w", encoding="utf-8").write(s.replace(OLD, NEW, 1))
print("OK — merge-perplexity retiré, flux Awin et page deals surveillés (sauvegarde %s.bak_cronlogs)" % P)
