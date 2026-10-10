#!/usr/bin/env python3
"""Ajoute les bannières promo (ex. SALE25 Solebox) au modèle de deals.html."""
import re, sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "PROMOS = [" in s:
    print("Déjà patché."); sys.exit(0)

promo_code = '''
# ── Bannières promo (affichées entre start et end, heure de Paris) ──
PROMOS = [
    {"code": "SALE25", "text": "FLASH SALE SOLEBOX", "label": "-25% jusqu'au 19/10",
     "url": "https://www.awin1.com/cread.php?awinmid=20964&awinaffid=2855487&ued=https%3A%2F%2Fwww.solebox.com%2Fc%2F4171",
     "start": "2026-10-10", "end": "2026-10-19"},
]
def promo_html():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
    out = []
    for p in PROMOS:
        if p["end"] < today:
            continue
        url = p["url"].replace("&", "&amp;")
        out.append(
            f'<div class="promo-banner" data-start="{p["start"]}" data-end="{p["end"]}" style="background:linear-gradient(90deg,#FF2D2D,#cc0000);color:#fff;text-align:center;padding:.55rem 1rem;font-size:.85rem;font-weight:700;letter-spacing:.05em">'
            f'🔥 {p["text"]} — <span style="background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.4);border-radius:4px;padding:.1rem .45rem;cursor:pointer" '
            f'onclick="navigator.clipboard&&navigator.clipboard.writeText(\\'{p["code"]}\\');this.textContent=\\'✅ Copié!\\'">{p["code"]}</span> = {p["label"]} &nbsp;'
            f'<a href="{url}" target="_blank" rel="nofollow sponsored noopener" style="color:#fff;text-decoration:underline">Voir les offres →</a></div>')
    if not out:
        return ""
    js = ("<script>(function(){var t=new Date().toLocaleDateString('sv-SE',{timeZone:'Europe/Paris'});"
          "document.querySelectorAll('.promo-banner').forEach(function(d){if(t<d.dataset.start||t>d.dataset.end)d.style.display='none';});})();</script>")
    return "\\n".join(out) + js
'''
anchor = "MAX_PER_SHOP = 400\n"
assert s.count(anchor) == 1, "ancre MAX_PER_SHOP introuvable"
s = s.replace(anchor, anchor + promo_code, 1)
tpl = '</header>\n<div class="tabs">'
assert s.count(tpl) == 1, "ancre </header> introuvable"
s = s.replace(tpl, '</header>\n{promo_html()}\n<div class="tabs">', 1)
shutil.copy(P, P + ".bak")
open(P, "w", encoding="utf-8").write(s)
print("OK — patché (sauvegarde : %s.bak)" % P)
