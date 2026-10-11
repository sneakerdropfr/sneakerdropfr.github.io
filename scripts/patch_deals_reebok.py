#!/usr/bin/env python3
"""deals_affilies.py : ajoute l'onglet Reebok (flux Awin « Reebok FR », baskets et chaussures adultes en stock)."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "def load_reebok(" in s:
    print("Déjà patché."); sys.exit(0)
if "def fr_link(" not in s:
    sys.exit("Le patch des liens /fr-fr/ doit être appliqué avant — rien modifié")
FUNC = '''def load_reebok():
    """Flux « Reebok FR » : baskets et chaussures adultes en stock, une entrée par modèle/coloris."""
    out, seen = [], set()
    if not os.path.exists(FEED_PATH): return out
    kids = ["enfant", "junior", "bébé", "bebe", "garçon", "garcon", "fille", "kids", "toddler", "infant", "baby"]
    with gzip.open(FEED_PATH, 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r.get('merchant_name', '') != 'Reebok FR' or r.get('in_stock', '') != '1': continue
            nm = (r.get('product_name', '') or '').replace('\\xa0', ' ').strip()
            low = nm.lower()
            if not ('baskets' in low or 'chaussures' in low): continue
            if any(k in low for k in kids): continue
            try: p = float(r.get('search_price', '0') or 0)
            except: continue
            if p <= 0: continue
            img = r.get('merchant_image_url', '') or r.get('large_image', '')
            if not img or img in seen: continue
            seen.add(img)
            nm = re.sub(r'^Reebok\\s*-\\s*', '', nm)
            nm = re.sub(r',\\s*[0-9][0-9.,/ ]*$', '', nm).strip(' ,')
            out.append({'name': nm, 'price': p, 'url': fr_link(r), 'img': img, 'brand': 'Reebok'})
    return sorted(out, key=lambda x: x['price'])[:MAX_PER_SHOP]
'''
R = [
 ('"solebox": "20964"}', '"solebox": "20964", "Reebok FR": "121522"}'),
 ("def load_bstn():", FUNC + "def load_bstn():"),
 ("def build(bstn,sn,sb):\n", "def build(bstn,sn,sb,rb=None):\n    rb=rb or []\n"),
 ("chez BSTN, Snipes et Solebox.", "chez BSTN, Snipes, Solebox et Reebok."),
 ("""<button class="tb" onclick="stab('solebox',this)">Solebox</button>""",
  """<button class="tb" onclick="stab('solebox',this)">Solebox</button>\n  <button class="tb" onclick="stab('reebok',this)">Reebok</button>"""),
 ("<footer>Liens affiliés Awin",
  """<div id="t-reebok" class="tc">\n  <div class="bar"><input class="si" id="s-reebok" type="text" placeholder="Rechercher…" oninput="rdr('reebok')"><select class="ss" id="o-reebok" onchange="rdr('reebok')"><option value="pa">Prix ↑</option><option value="pd">Prix ↓</option><option value="az">A–Z</option></select></div>\n  <div class="cnt" id="n-reebok"></div><div class="grid" id="g-reebok"></div>\n</div>\n<footer>Liens affiliés Awin"""),
 ("const SB={json.dumps(sb,ensure_ascii=False)};", "const SB={json.dumps(sb,ensure_ascii=False)};\nconst RB={json.dumps(rb,ensure_ascii=False)};"),
 ("const DATA={{bstn:BD,snipes:SN,solebox:SB}};", "const DATA={{bstn:BD,snipes:SN,solebox:SB,reebok:RB}};"),
 ("solebox:{{b:'',s:'pa'}}}};", "solebox:{{b:'',s:'pa'}},reebok:{{b:'',s:'pa'}}}};"),
 ("html=build(bstn,sn,sb)", "rb=load_reebok()\n    print(f\"Reebok:{len(rb)}\")\n    html=build(bstn,sn,sb,rb)"),
]
for a, b in R:
    if s.count(a) != 1:
        sys.exit("Ancre introuvable ou multiple — rien modifié : " + a[:60])
for a, b in R:
    s = s.replace(a, b, 1)
shutil.copy(P, P + ".bak_reebok")
open(P, "w", encoding="utf-8").write(s)
print("OK — onglet Reebok ajouté (sauvegarde %s.bak_reebok)" % P)
