#!/usr/bin/env python3
"""Ajoute la colonne merchant_product_category_path aux adresses des flux Awin (/root/.awin_feed_url),
sans jamais les afficher, puis relance le téléchargement des flux."""
import os, re, sys, shutil, subprocess
F = "/root/.awin_feed_url"
COL = "merchant_product_category_path"
lines = open(F, encoding="utf-8").read().splitlines()
out, added, skipped, nocol = [], 0, 0, 0
for l in lines:
    t = l.strip()
    if not t or t.startswith("#"):
        out.append(l); continue
    if COL in t:
        skipped += 1; out.append(l); continue
    m = re.search(r"/columns/([^/?]+)", t)
    if not m:
        nocol += 1; out.append(l); continue
    t = t[:m.end(1)] + "%2C" + COL + t[m.end(1):]
    added += 1; out.append(t)
print("Adresses : %d complétée(s), %d déjà OK, %d sans liste de colonnes" % (added, skipped, nocol))
if added:
    shutil.copy(F, F + ".bak_cat")
    open(F, "w", encoding="utf-8").write("\n".join(out) + "\n")
    os.chmod(F, 0o600)
    print("Fichier mis à jour (sauvegarde %s.bak_cat)" % F)
U = "/root/awin_feed_update.py"
if not os.path.exists(U):
    sys.exit("awin_feed_update.py introuvable dans /root — flux non relancé")
print("=== Téléchargement des flux ===", flush=True)
r = subprocess.run([sys.executable, U])
if r.returncode: sys.exit("Échec du téléchargement des flux")
