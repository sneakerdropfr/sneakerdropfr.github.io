#!/usr/bin/env python3
"""deals_affilies.py : bannières Singles Day — Snipes (-20 %, 07/11 → 11/11) et Reebok (jusqu'à -40 %, 08/11 → 11/11)."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "SINGLES DAY SNIPES" in s:
    print("Déjà patché."); sys.exit(0)
ENTRY = '''PROMOS = [
    {"code": "", "text": "SINGLES DAY SNIPES", "label": "-20% sur une sélection, du 07/11 au 11/11",
     "url": "https://www.awin1.com/cread.php?awinmid=122628&awinaffid=2855487&ued=https%3A%2F%2Fwww.snipes.com%2Ffr-fr%2Fc%2Fsale-660",
     "start": "2026-11-07", "end": "2026-11-11"},
    {"code": "", "text": "SINGLES' DAY REEBOK", "label": "Jusqu'à -40% + 10% en plus dès 2 articles, du 08/11 au 11/11",
     "url": "https://www.awin1.com/cread.php?awinmid=121522&awinaffid=2855487&ued=https%3A%2F%2Fwww.reebok.eu%2Ffr-fr%2Fcollections%2Fsingles-day",
     "start": "2026-11-08", "end": "2026-11-11"},
'''
if s.count("PROMOS = [\n") != 1:
    sys.exit("Ancre PROMOS introuvable — rien modifié")
shutil.copy(P, P + ".bak_singles_day")
open(P, "w", encoding="utf-8").write(s.replace("PROMOS = [\n", ENTRY, 1))
print("OK — bannières Singles Day Snipes (07/11–11/11) et Reebok (08/11–11/11) ajoutées (sauvegarde " + P + ".bak_singles_day)")
