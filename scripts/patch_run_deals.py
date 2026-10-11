#!/usr/bin/env python3
"""Installe deals_sync_deploy.py et l'appelle à la fin de run_deals.sh."""
import sys, shutil, urllib.request, os, py_compile
RD = sys.argv[1] if len(sys.argv) > 1 else "/root/run_deals.sh"
DST = "/root/deals_sync_deploy.py"
URL = "https://raw.githubusercontent.com/sneakerdropfr/sneakerdropfr.github.io/main/scripts/deals_sync_deploy.py"
if not os.path.exists(RD): sys.exit("run_deals.sh introuvable : " + RD)
data = urllib.request.urlopen(URL + "?t=1", timeout=30).read()
open(DST, "wb").write(data); py_compile.compile(DST, doraise=True)
s = open(RD, encoding="utf-8").read()
if "deals_sync_deploy.py" in s:
    print("run_deals.sh appelle déjà deals_sync_deploy.py (script mis à jour)"); sys.exit(0)
shutil.copy(RD, RD + ".bak_sync")
if not s.endswith(chr(10)): s += chr(10)
s += "# Copie deals.html sur perplexity + lance le déploiement GitHub Pages" + chr(10) + "python3 " + DST + chr(10)
open(RD, "w", encoding="utf-8").write(s)
print("OK — run_deals.sh appellera deals_sync_deploy.py (sauvegarde %s.bak_sync)" % RD)
