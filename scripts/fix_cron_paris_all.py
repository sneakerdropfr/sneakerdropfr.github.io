#!/usr/bin/env python3
"""Crontab : autres tâches du VPS calées sur l'heure de Paris (heures d'été d'origine conservées).
Le VPS est en UTC : chaque tâche est lancée aux deux heures UTC possibles et /root/at_paris.sh
ne laisse passer que l'heure de Paris voulue. Les scripts eux-mêmes ne sont pas modifiés."""
import subprocess, sys, os, re
W = "/root/at_paris.sh"
open(W, "w").write(
    '#!/bin/bash\n'
    '# usage : at_paris.sh HH[,HH...] [commande...]\n'
    '# sans commande : code retour 0 si l\'heure de Paris est dans la liste, 1 sinon\n'
    'h=$(TZ=Europe/Paris date +%H)\n'
    'case ",$1," in *",$h,"*) ;; *) exit 1 ;; esac\n'
    'shift\n'
    '[ $# -eq 0 ] && exit 0\n'
    'exec "$@"\n')
os.chmod(W, 0o755)
NAMES = ["bstn_upcoming.py", "health_check.py", "image_hunter.py", "daily_digest.py",
         "bstn_github.py", "bstn_promos_github.py", "bstn_restock_sync.py"]
cur = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
out, done = [], []
for l in cur.splitlines():
    s = l.strip()
    hit = next((n for n in NAMES if "/root/" + n in s), None)
    if not hit or s.startswith("#") or "at_paris.sh" in s:
        out.append(l); continue
    f = s.split(None, 5)
    if len(f) < 6 or not re.fullmatch(r"\d+(,\d+)*", f[1]):
        print("Ignorée (heure non fixe) :", hit); out.append(l); continue
    paris = sorted({(int(h) + 2) % 24 for h in f[1].split(",")})          # heure voulue = heure d'été
    utc = sorted({(p - k) % 24 for p in paris for k in (1, 2)})          # hiver +1, été +2
    hh = ",".join("%02d" % p for p in paris)
    out.append("%s %s %s %s %s /bin/bash %s %s && %s" % (f[0], ",".join(map(str, utc)), f[2], f[3], f[4], W, hh, f[5]))
    done.append("%s : %s h Paris" % (hit, hh))
if not done:
    print("Rien à modifier (déjà fait ?)"); sys.exit(0)
open("/root/crontab.bak_paris_all", "w").write(cur)
p = subprocess.run(["crontab", "-"], input="\n".join(out) + "\n", text=True)
if p.returncode: sys.exit("Échec crontab — sauvegarde dans /root/crontab.bak_paris_all")
print("OK — sauvegarde /root/crontab.bak_paris_all")
for d in done: print("  " + d)
