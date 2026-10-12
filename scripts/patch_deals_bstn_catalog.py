#!/usr/bin/env python3
"""deals_affilies.py : onglet « BSTN Catalogue » (flux Awin BSTN FR : chaussures adultes des marques sneakers, en stock).
L'onglet BSTN existant (drops à venir depuis releases.json) devient « BSTN Drops »."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "def load_bstn_catalog(" in s:
    print("Déjà patché."); sys.exit(0)
if "def load_reebok(" not in s or "def fr_link(" not in s:
    sys.exit("Les patchs Reebok et liens /fr-fr/ doivent être appliqués avant — rien modifié")
FUNC = r'''BSTN_BRANDS = ['nike','jordan','adidas','new balance','asics','vans','puma','converse','reebok','saucony','salomon',
    'hoka','on','brooks','mizuno','timberland','ugg','birkenstock','crocs','clarks']
BSTN_EXCL = re.compile(r'(?<!\w)(?:t-?shirts?|tees?|shorts?|hoodies?|hoody|socks?|jerseys?|caps?|hats?|beanies?|bags?|inserts?|pants?|jackets?|'
    r'sweat\w*|crew|pullovers?|vests?|bras?|leggings?|tights?|skirts?|dress|gloves?|scarf|wallets?|backpacks?|belts?|fleece|'
    r'track\w*|trousers?|joggers?|cleaner|laces?|towels?|balls?|bottles?|keychains?|cases?|stickers?|umbrellas?|pack|\d+-pack|'
    r'ankle|bodysuits?|deflated|headbands?|trunks?|briefs?|boxers?|wristbands?|sleeves?|polos?|tank|anorak|parka|coats?|'
    r'sweaters?|cardigans?|knit|bucket|visor|pouch|tote|mask|bandana|lanyard|tube|poster|book|candle|spray|protector|brush|'
    r'kids|youth|junior|baby|infant|toddler|little|\(ps\)|\(gs\)|\(td\)|\(bg\)|\(gg\)|\(inf\)|size \d+)(?=\W|$)', re.IGNORECASE)
def load_bstn_catalog(limit=600):
    """Flux « BSTN FR » : chaussures adultes en stock des marques sneakers, une entrée par image."""
    out, seen = [], set()
    if not os.path.exists(FEED_PATH): return out
    with gzip.open(FEED_PATH, 'rt', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r.get('merchant_name', '') != 'BSTN FR' or r.get('in_stock', '') != '1': continue
            bn = (r.get('brand_name', '') or '').strip()
            if bn.lower() not in BSTN_BRANDS: continue
            nm = (r.get('product_name', '') or '').replace('\xa0', ' ').strip()
            if not nm or BSTN_EXCL.search(nm): continue
            try: p = float(r.get('search_price', '0') or 0)
            except: continue
            if p <= 0: continue
            img = r.get('merchant_image_url', '') or r.get('large_image', '')
            if not img or img in seen: continue
            seen.add(img)
            br = extract_brand(bn)
            if bn.lower() not in nm.lower(): nm = br + ' ' + nm
            try: old = float(r.get('product_price_old', '0') or 0)
            except: old = 0
            out.append({'name': nm, 'price': p, 'url': fr_link(r), 'img': img, 'brand': br, '_promo': old > p})
    out.sort(key=lambda x: (not x['_promo'], x['price']))
    out = out[:limit]
    for x in out: x.pop('_promo', None)
    return sorted(out, key=lambda x: x['price'])
'''
TAB = '''<div id="t-bstncat" class="tc">
  <div class="bar"><input class="si" id="s-bstncat" type="text" placeholder="Rechercher…" oninput="rdr('bstncat')"><select class="ss" id="o-bstncat" onchange="rdr('bstncat')"><option value="pa">Prix ↑</option><option value="pd">Prix ↓</option><option value="az">A–Z</option></select></div>
  <div class="brands" id="br-bstncat">{bb_html(top_brands(bc),'bstncat')}</div>
  <div class="cnt" id="n-bstncat"></div><div class="grid" id="g-bstncat"></div>
</div>
<div id="t-snipes" class="tc">'''
R = [
 ('"Reebok FR": "121522"}', '"Reebok FR": "121522", "BSTN FR": "104979"}'),
 ("def load_bstn():", FUNC + "def load_bstn():"),
 ("def build(bstn,sn,sb,rb=None):\n    rb=rb or []\n", "def build(bstn,sn,sb,rb=None,bc=None):\n    rb=rb or []\n    bc=bc or []\n"),
 ("""<button class="tb on" onclick="stab('bstn',this)">BSTN</button>""",
  """<button class="tb on" onclick="stab('bstn',this)">BSTN Drops</button>\n  <button class="tb" onclick="stab('bstncat',this)">BSTN Catalogue</button>"""),
 ('<div id="t-snipes" class="tc">', TAB),
 ("const BD={json.dumps(bstn,ensure_ascii=False)};", "const BD={json.dumps(bstn,ensure_ascii=False)};\nconst BC={json.dumps(bc,ensure_ascii=False)};"),
 ("const DATA={{bstn:BD,", "const DATA={{bstn:BD,bstncat:BC,"),
 ("const STA={{bstn:{{b:'',s:'date'}},", "const STA={{bstn:{{b:'',s:'date'}},bstncat:{{b:'',s:'pa'}},"),
 ("    rb=load_reebok()\n", "    rb=load_reebok()\n    bc=load_bstn_catalog()\n    print(f\"BSTN catalogue:{len(bc)}\")\n"),
 ("html=build(bstn,sn,sb,rb)", "html=build(bstn,sn,sb,rb,bc)"),
 (".tc{{display:none;padding:18px 20px}}", ".tabs{{overflow-x:auto;scrollbar-width:none}}.tabs::-webkit-scrollbar{{display:none}}.tb{{white-space:nowrap;flex-shrink:0}}\n.tc{{display:none;padding:18px 20px}}"),
]
for a, b in R:
    if s.count(a) != 1:
        sys.exit("Ancre introuvable ou multiple — rien modifié : " + a.strip()[:60])
for a, b in R:
    s = s.replace(a, b, 1)
shutil.copy(P, P + ".bak_bstncat")
open(P, "w", encoding="utf-8").write(s)
print("OK — onglet BSTN Catalogue ajouté (sauvegarde %s.bak_bstncat)" % P)
