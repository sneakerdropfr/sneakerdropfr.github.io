#!/usr/bin/env python3
"""deals_affilies.py : en-tête identique aux autres pages (logo SneakerDropFR, bouton Accueil, styles communs)."""
import sys, shutil, re
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "_site_header" in s:
    print("Déjà patché."); sys.exit(0)
HEADER_RE = r'<header>\s*<a class="back" href="/">← Accueil</a>\s*<h1>Sneakers Deals</h1>\s*<span class="ts">Màj \{now\}</span>\s*</header>'
NEW_HEADER = '''<header class="header">
  <div class="container header__inner">
    <a href="/" class="logo"><div class="logo__icon"><img src="/assets/images/sneakerdropfr-logo.svg" alt="SneakerDropFR" width="30" height="30" style="display:block"></div><span>SneakerDrop<span class="logo__fr">FR</span></span></a>
    <div class="header__spacer"></div>
    <a href="/" class="hbtn hbtn--back">← Accueil</a>
  </div>
</header>'''
LINKS = ('<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:wght@400;600;700;900&family=Barlow+Condensed:wght@400;700;900&display=swap" rel="stylesheet" />\n'
         '<link rel="stylesheet" href="/assets/css/shared.css" />\n<style>  /* _site_header */\n'
         '.dhead{{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;padding:18px 20px 6px}}\n'
         '.dtitle{{font-family:var(--font-cond,sans-serif);font-size:30px;font-weight:900;letter-spacing:.02em;text-transform:uppercase;color:var(--tx)}}\n'
         '.dhead .ts{{font-size:11px;color:var(--mu)}}\n'
         'body{{padding-bottom:0}}\n')
n_head = len(re.findall(HEADER_RE, s))
n_style = s.count("<style>\n:root{{--bg:")
n_promo = s.count('{promo_html()}\n<div class="tabs">')
if n_head != 1 or n_style != 1 or n_promo != 1:
    sys.exit("Ancre introuvable ou multiple — rien modifié (en-tête %d, style %d, promo %d)" % (n_head, n_style, n_promo))
s = re.sub(HEADER_RE, lambda m: NEW_HEADER, s, count=1)
s = s.replace("<style>\n:root{{--bg:", LINKS + ":root{{--bg:", 1)
s = re.sub(r'header\{\{background:#111;[^}]*\}\}\n?', '', s, count=1)
s = re.sub(r'header h1\{\{[^}]*\}\}\n?', '', s, count=1)
s = s.replace('{promo_html()}\n<div class="tabs">',
              '{promo_html()}\n<div class="dhead"><h1 class="dtitle">Sneakers Deals</h1><span class="ts">Màj {now}</span></div>\n<div class="tabs">', 1)
shutil.copy(P, P + ".bak_header")
open(P, "w", encoding="utf-8").write(s)
print("OK — en-tête identique aux autres pages (sauvegarde %s.bak_header)" % P)
