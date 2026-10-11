#!/usr/bin/env python3
"""deals_affilies.py : liens Snipes/Solebox vers les boutiques françaises (/fr-fr/) via Awin cread."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "def fr_link(" in s:
    print("Déjà patché."); sys.exit(0)
FUNC = '''
# ── Liens vers les boutiques françaises (/fr-fr/) avec suivi Awin ──
AWIN_MIDS = {"Snipes EU": "122628", "solebox": "20964"}
def fr_link(r):
    import urllib.parse as _up
    dl = (r.get("merchant_deep_link") or "").split("?")[0]
    mid = AWIN_MIDS.get(r.get("merchant_name", ""))
    if dl and mid and re.search(r"/[a-z]{2}-[a-z]{2}/", dl):
        fr = re.sub(r"/[a-z]{2}-[a-z]{2}/", "/fr-fr/", dl, count=1)
        return "https://www.awin1.com/cread.php?awinmid=%s&awinaffid=2855487&ued=%s" % (mid, _up.quote(fr, safe=""))
    return r.get("aw_deep_link", "")
'''
anchor = "MAX_PER_SHOP = 400\n"
old = "'url':r.get('aw_deep_link','')"
if s.count(anchor) != 1 or s.count(old) != 1:
    sys.exit("Ancre introuvable — rien modifié")
s = s.replace(anchor, anchor + FUNC, 1).replace(old, "'url':fr_link(r)", 1)
shutil.copy(P, P + ".bak_fr")
open(P, "w", encoding="utf-8").write(s)
print("OK — liens /fr-fr/ activés (sauvegarde %s.bak_fr)" % P)
