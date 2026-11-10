#!/usr/bin/env python3
"""Crontab : bstn_feed.py (Telegram « SORTIE DU JOUR ») calé sur l'heure de Paris, été comme hiver.
Le VPS est en UTC : la tâche est lancée aux deux heures UTC possibles et /root/at_paris.sh
ne laisse passer que celle qui correspond à l'heure de Paris voulue (8h45 et 21h00).
bstn_feed.py n'est pas modifié."""
import subprocess, sys, os
W = "/root/at_paris.sh"
open(W, "w").write('#!/bin/bash\n# usage : at_paris.sh HH commande... (ne lance que si l\'heure de Paris vaut HH)\n'
                   '[ "$(TZ=Europe/Paris date +%H)" = "$1" ] || exit 0\nshift\nexec "$@"\n')
os.chmod(W, 0o755)
cur = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
R = {
 "45 6 * * * python3 /root/bstn_feed.py >> /root/bstn.log 2>&1":
 "45 6,7 * * * /bin/bash /root/at_paris.sh 08 python3 /root/bstn_feed.py >> /root/bstn.log 2>&1",
 "0 19 * * * python3 /root/bstn_feed.py >> /root/bstn.log 2>&1":
 "0 19,20 * * * /bin/bash /root/at_paris.sh 21 python3 /root/bstn_feed.py >> /root/bstn.log 2>&1",
}
lines = cur.splitlines(); n = 0
for i, l in enumerate(lines):
    if l.strip() in R:
        lines[i] = R[l.strip()]; n += 1
if n == 0:
    print("Déjà fait." if "at_paris.sh 08 python3 /root/bstn_feed.py" in cur else "Lignes bstn_feed introuvables — rien modifié"); sys.exit(0)
if n != 2:
    sys.exit("Une seule des deux lignes trouvée — rien modifié")
open("/root/crontab.bak_paris", "w").write(cur)
p = subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True)
if p.returncode: sys.exit("Échec crontab — sauvegarde dans /root/crontab.bak_paris")
print("OK — bstn_feed.py : 8h45 et 21h00 heure de Paris (sauvegarde /root/crontab.bak_paris)")
print("Test maintenant : heure de Paris =", subprocess.run(["bash", "-c", "TZ=Europe/Paris date +%H:%M"], capture_output=True, text=True).stdout.strip())
