#!/usr/bin/env python3
"""SneakerDropFR — tâches planifiées (pages publiques WhenToCop uniquement, aucun token WTC/Cloudflare).

Usage : python3 sneakerdrop_jobs.py <week|daily|releases8|restocks> [--dry-run]
  week      : semaine en cours → ajoute les paires WTC manquantes, complète les retailers, reconstruit weekly_data.json
  daily     : lot de 10 fiches (curseur cursor.json) → date/prix si fiche sans retailers, nouveaux retailers, purge passées
  releases8 : ajoute les drops WTC des 8 prochaines semaines absents de releases.json
  restocks  : rafraîchit les fiches existantes de restocks.json (retire les passées, complète les retailers)

GitHub via `gh api` (accès GitHub intégré, api_credentials=['github']). Push perplexity ET main, commits [skip ci].

Règles :
- Fiche existante AVEC retailers : on n'ajoute que les retailers nouveaux trouvés sur la page publique WTC. Rien d'autre ne change.
- Fiche existante SANS retailers : date/prix peuvent être mis à jour depuis la page WTC, retailers ajoutés.
- Titres jamais modifiés. image_url commençant par /images/ jamais modifiée. Images WTC téléchargées localement.
- Retailers : uniquement ceux chargés par la page publique WTC de la paire ; bannis et liens génériques filtrés ; Awin BSTN/Solebox/Snipes réécrits.
- Marques autorisées détectées dans le nom (« New Balance 204L », « Rosé x Puma … »). Vêtements et SKUs bannis exclus.
"""
import json, re, sys, base64, subprocess, tempfile, os, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote
from zoneinfo import ZoneInfo

DRY = '--dry-run' in sys.argv
REPO = 'sneakerdropfr/sneakerdropfr.github.io'
API = f'repos/{REPO}/contents/'
BRANCHES = ['perplexity', 'main']
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36', 'Accept-Language': 'fr-FR'}
CANON = {'air jordan': 'Air Jordan', 'new balance': 'New Balance', 'nike': 'Nike', 'adidas': 'Adidas', 'jordan': 'Jordan',
         'puma': 'Puma', 'vans': 'Vans', 'converse': 'Converse', 'reebok': 'Reebok', 'asics': 'ASICS', 'saucony': 'Saucony',
         'brooks': 'Brooks', 'salomon': 'Salomon'}
CLOTHING = re.compile(r'\b(hoodie|shirt|t-shirt|pants?|tee|jacket|cap|hat|socks?|shorts|jersey|sweater|fleece|vest|crewneck|bag|beanie|sweatpants|joggers?|sweatshirt|trousers|tracksuit|hoodies|long-sleeve)\b', re.I)
BANNED_SKUS = {'KK2600', 'KK2599', 'KJ2419'}
LOCKED_SKUS = {'HV0823-101', 'KJ4289'}
BANNED_RETAILERS = {'stockx', 'goat', 'limited resell', 'klekt', 'restocks', 'laced', 'stadium goods', 'flight club', 'alias', 'bump'}
AWIN_AFFID = '2855487'
AWIN_MIDS = {'bstn': '104979', 'solebox': '20964', 'snipes': '122628'}
GENERIC_URL = re.compile(r'/c/sneakers|/men/all|/women/all|prefn1=|/search\?|/collections/|\?q=|/all-products|/latest/|/fr-fr/c/|/en/c/', re.I)
MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
TODAY = datetime.now(ZoneInfo('Europe/Paris')).date()
LUNDI = TODAY - timedelta(days=TODAY.weekday())
DIMANCHE = LUNDI + timedelta(days=6)


# ───────── GitHub ─────────
def gh(args, payload=None):
    path = None
    if payload is not None:
        f = tempfile.NamedTemporaryFile('w', delete=False, suffix='.json'); json.dump(payload, f); f.close()
        path = f.name; args = args + ['--input', path]
    o = subprocess.run(['gh', 'api'] + args, capture_output=True, text=True)
    if path: os.unlink(path)
    return o

def gh_get(fn, branch):
    o = gh([f'{API}{fn}?ref={branch}'])
    if o.returncode != 0: return None, None
    m = json.loads(o.stdout)
    if m.get('content'):
        return base64.b64decode(m['content']), m['sha']
    # fichiers > 1 Mo : passer par l'API blobs
    b = gh([f"repos/{REPO}/git/blobs/{m['sha']}"])
    return base64.b64decode(json.loads(b.stdout)['content']), m['sha']

_BASE = {}  # contenu lu par le job, par fichier (garde-fou de synchronisation)

def gh_json(fn, branch='main'):
    raw, _ = gh_get(fn, branch)
    if fn not in _BASE: _BASE[fn] = raw
    return json.loads(raw) if raw else None

def branches_ok(fn):
    """Avant toute écriture : main et perplexity doivent être identiques entre elles
    ET identiques à la version lue par le job. Sinon on n'écrase rien."""
    cur = {b: gh_get(fn, b)[0] for b in BRANCHES}
    if cur['main'] != cur['perplexity']:
        print(f'  ERREUR SYNC {fn} : main et perplexity diffèrent — écriture annulée, vérifier quelle version est la plus récente')
        return False
    if fn in _BASE and _BASE[fn] is not None and cur['main'] != _BASE[fn]:
        print(f'  ERREUR SYNC {fn} : modifié par un autre outil pendant le job — écriture annulée')
        return False
    return True

def gh_put(fn, raw, msg, branch):
    if not msg.startswith('[skip ci]'): msg = '[skip ci] ' + msg
    for attempt in range(2):
        _, sha = gh_get(fn, branch)
        body = {'message': msg, 'content': base64.b64encode(raw).decode(), 'branch': branch}
        if sha: body['sha'] = sha
        o = gh(['-X', 'PUT', API + fn], body)
        if '"commit"' in o.stdout: return True
        if attempt == 0 and re.search(r'409|422', o.stdout + o.stderr): time.sleep(3); continue
        print(f'  ERREUR PUT {fn}@{branch}: {(o.stdout + o.stderr)[:200]}'); return False
    return False

def push_json(fn, data, msg):
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode()
    if DRY: print(f'  [dry-run] {fn} non poussé ({msg})'); return True
    if not branches_ok(fn): return False
    ok = all(gh_put(fn, raw, msg, b) for b in BRANCHES)
    if ok: _BASE[fn] = raw
    return ok


# ───────── WhenToCop (pages publiques) ─────────
def http(url):
    try: return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
    except urllib.error.HTTPError as e: return None if e.code == 404 else b''
    except Exception: return b''

# WhenToCop est passé sous Astro (oct. 2026) : les données sont dans les props des <astro-island>
# (format sérialisé [type, valeur] : 0 = valeur, 1 = tableau).
_MOIS_FR = {m: i + 1 for i, m in enumerate(['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'])}

def _astro_dec(v):
    if isinstance(v, list) and len(v) == 2 and isinstance(v[0], int):
        t, x = v
        if t == 0: return {k: _astro_dec(y) for k, y in x.items()} if isinstance(x, dict) else x
        if t == 1: return [_astro_dec(y) for y in x]
        return x
    if isinstance(v, dict): return {k: _astro_dec(y) for k, y in v.items()}
    return v

def astro_islands(url):
    """Liste (composant, props) de la page ; None si 404, [] si échec réseau."""
    import html as _html
    h = http(url)
    if h is None: return None
    if not h: return []
    out = []
    for m in re.finditer(r'<astro-island\b([^>]*)>', h.decode('utf-8', 'ignore')):
        at = m.group(1)
        ce = re.search(r'component-export="([^"]*)"', at); pr = re.search(r'\sprops="([^"]*)"', at)
        if not pr: continue
        try: out.append((ce.group(1) if ce else '', {k: _astro_dec(v) for k, v in json.loads(_html.unescape(pr.group(1))).items()}))
        except Exception: pass
    return out

def _fr_date(txt):
    """« Jeudi 22 octobre 2026 » ou « 22/10/2026 » → '2026-10-22' (None si inconnue)."""
    txt = (txt or '').strip().lower()
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', txt)
    if m: return f'{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}'
    m = re.search(r'(\d{1,2})\s+([a-zéû]+)\s+(\d{4})', txt)
    if m and m.group(2) in _MOIS_FR: return f'{m.group(3)}-{_MOIS_FR[m.group(2)]:02d}-{int(m.group(1)):02d}'
    return None

def _card_obj(prod):
    """Carte du calendrier → dict au format utilisé par le reste du script."""
    c = prod.get('card') or {}; tr = c.get('track') or {}; dr = c.get('drop') or {}
    slug = (c.get('href') or '').split('/drops/')[-1].strip('/')
    d = _fr_date(prod.get('day'))
    img = (c.get('image') or {}).get('url') or ''
    if not slug or not d: return None
    return {'slug': slug, 'styleCode': tr.get('sku') or '', 'brandName': tr.get('brandName') or dr.get('brandName') or '',
            'modelName': tr.get('modelName') or dr.get('modelName') or '', 'dropDate': d, 'isDropDateKnown': True,
            'retailPrice': dr.get('retailPrice') or 0, 'mainImages': [{'url': img}] if img else [],
            'productCategoryId': 2 if (dr.get('productCategory') in (None, 'sneakers') and dr.get('isSneaker', True)) else 99}

def wtc_list(max_date, max_pages=15):
    """Drops publics à partir d'aujourd'hui, triés par date (pagination /drops?page=N)."""
    found = {}
    for p in range(1, max_pages + 1):
        isl = astro_islands(f'https://www.whentocop.fr/drops?page={p}') or []
        cat = next((pr for n, pr in isl if n == 'ProductCatalogue' and 'initialPage' in pr), None)
        if not cat: break
        items = [o for o in (_card_obj(x) for x in cat['initialPage'].get('products') or []) if o]
        if not items: break
        for o in items: found.setdefault(o['slug'], o)
        ip = cat['initialPage']
        if max(o['dropDate'] for o in items) > str(max_date): break
        if (ip.get('offset') or 0) + len(ip.get('products') or []) >= (ip.get('total') or 0): break
        time.sleep(1)
    return found

_DETAIL = {}
def wtc_detail(slug):
    """Fiche publique d'une paire (None si la page n'existe pas, {} si illisible). '_offers' = retailers chargés par la page."""
    if slug in _DETAIL: return _DETAIL[slug]
    isl = astro_islands(f'https://www.whentocop.fr/drops/{slug}')
    if isl is None: _DETAIL[slug] = None; return None
    po = next((pr for n, pr in isl if n == 'ProductOffers'), None)
    ac = next((pr.get('drop') for n, pr in isl if n == 'AddToCollectionButton' and isinstance(pr.get('drop'), dict)), None) or {}
    if not po: return {}
    dr = po.get('drop') or {}
    offers = po.get('retailerOffers') or []
    d = ac.get('releaseDate') or next((_fr_date(o.get('dropDate')) for o in offers if _fr_date(o.get('dropDate'))), None)
    out = {'slug': dr.get('slug') or slug, 'styleCode': dr.get('styleCode') or '', 'brandName': dr.get('brandName') or '',
           'modelName': dr.get('modelName') or '', 'retailPrice': dr.get('retailPrice') or ac.get('retailPrice') or 0,
           'dropDate': d or '', 'isDropDateKnown': bool(d), '_offers': offers,
           '_shops': (po.get('comparator') or {}).get('catalogs') or []}
    _DETAIL[slug] = out
    time.sleep(1)
    return out

def detect_brand(name):
    low = (name or '').lower()
    for k in sorted(CANON, key=len, reverse=True):
        if re.search(r'(?<![a-z])' + re.escape(k) + r'(?![a-z])', low): return CANON[k]
    return None

def eligible(o):
    name = f"{o.get('brandName') or ''} {o.get('modelName') or ''}".strip()
    sku = (o.get('styleCode') or '').upper()
    if o.get('isDropDateKnown') is False: return None, 'date inconnue'
    if o.get('productCategoryId') not in (None, 2): return None, 'pas une sneaker'
    brand = detect_brand(o.get('brandName') or name)
    if not brand: return None, 'marque non autorisée'
    if CLOTHING.search(name): return None, 'vêtement'
    if sku in BANNED_SKUS: return None, 'SKU banni'
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9-]{3,}', sku): return None, 'SKU invalide'
    return brand, ''

def best_image(o):
    imgs = o.get('mainImages') or []
    return next((i['url'] for i in imgs if '2000x2000' in i.get('url', '')), imgs[0]['url'] if imgs else '')

def new_entry(o, brand):
    d = str(o['dropDate'])[:10]; y, m, dd = d.split('-')
    return {'id': o['slug'], 'slug': o['slug'], 'featured': False, 'year': int(str(o['dropDate'])[:4]), 'sku': (o.get('styleCode') or '').upper(),
            'title': f"{o.get('brandName') or ''} {o.get('modelName') or ''}".strip(), 'brand': brand, 'date': d,
            'date_display': f'{int(dd)} {MOIS[int(m) - 1]} {y}', 'price': int(float(o.get('retailPrice') or 0)),
            'image_url': '', '_img': best_image(o), 'wtc_url': 'https://www.whentocop.fr/drops/' + o['slug'], 'retailers': []}

def localize_image(e, folder='images'):
    src = e.pop('_img', '')
    if str(e.get('image_url', '')).startswith('/images/') or not src: return
    safe = re.sub(r'[^a-zA-Z0-9-]', '-', e['sku'])[:40]
    ext = src.rsplit('.', 1)[-1].lower() if src.rsplit('.', 1)[-1].lower() in ('webp', 'jpg', 'jpeg', 'png') else 'webp'
    path = f'{folder}/{safe}.{ext}'
    data = http(src)
    if not data or len(data) < 5000: return
    if DRY or all(gh_put(path, data, f'[skip ci] image: {path}', b) for b in BRANCHES): e['image_url'] = '/' + path


class Retailers:
    """Retailers chargés par la page publique WTC de la paire (lus dans la page, sans navigateur)."""
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def get(self, slug, price=0):
        d = wtc_detail(slug)
        if not d or '_offers' not in d:
            print(f'    retailers indisponibles pour {slug} ({"page absente" if d is None else "page illisible"})'); return None
        def clean(name, link):
            if not name or not link or name.lower() in BANNED_RETAILERS or is_generic(link): return None
            if 'awin1.com' in link:
                for k, mid in AWIN_MIDS.items():
                    if k in link.lower() or k in name.lower():
                        link = re.sub(r'awinaffid=\d+', f'awinaffid={AWIN_AFFID}', link)
                        link = re.sub(r'awinmid=\d+', f'awinmid={mid}', link); break
            return link
        # Section « Shops » : lien produit et prix propres à chaque magasin
        shops = {}
        for c in d.get('_shops') or []:
            it = c.get('items') or []; lo = c.get('lowestPrice') or (it[0] if it else {})
            name = ((c.get('infoReseller') or {}).get('name') or c.get('partner') or '').strip()
            pe = lo.get('salePriceEUR') or lo.get('priceEUR') or lo.get('price')
            if name and it: shops[name.lower()] = (name, (lo.get('url') or '').strip(), int(round(float(pe))) if pe else 0)
        out, seen = [], set()
        # 1) offres de sortie (FCFS / raffle)
        for r in d['_offers']:
            o = r.get('offer') or {}
            name = (o.get('retailerName') or '').strip()
            if name.lower() in seen: continue
            link = clean(name, (o.get('link') or (r.get('cta') or {}).get('url') or '').strip())
            if not link: continue
            sp = shops.get(name.lower())
            pr = sp[2] if sp and sp[2] else price
            out.append({'name': name, 'url': link, 'price': f'{pr}€' if pr else ''}); seen.add(name.lower())
        # 2) magasins de la section « Shops » absents des offres
        for key, (name, url, pr) in shops.items():
            if key in seen: continue
            link = clean(name, url)
            if not link: continue
            pr = pr or price
            out.append({'name': name, 'url': link, 'price': f'{pr}€' if pr else ''}); seen.add(key)
        return out


def is_generic(link):
    """Lien générique : page catégorie/recherche, page d'accueil ou placeholder WTC."""
    from urllib.parse import urlparse
    if 'defaultdropcreation' in link.lower(): return True
    m = re.search(r'[?&](?:ued|u|p|murl|url|wgtarget)=([^&]+)', link)
    dest = unquote(m.group(1)) if m else link
    if GENERIC_URL.search(dest): return True
    path = urlparse(dest).path.strip('/').lower()
    return path in ('', 'fr', 'fr-fr', 'fr_fr', 'eu_fr', 'en', 'fr/fr', 'fr/launch', 'launch')


def merge_retailers(entry, found):
    """Ajoute seulement les retailers absents (par nom). Retourne le nombre ajouté."""
    if not found: return 0
    have = {(r.get('name') or '').lower() for r in entry.get('retailers') or []}
    add = [r for r in found if r['name'].lower() not in have]
    if add: entry['retailers'] = (entry.get('retailers') or []) + add
    return len(add)

def slug_of(e):
    return e.get('slug') or (e.get('wtc_url') or '').split('/drops/')[-1].strip('/') or ''

def sort_key(x): return (x.get('date') in ('', 'TBD', None, '?'), x.get('date') or '')


# ───────── Tâches ─────────
def job_week():
    print(f'[week] semaine {LUNDI} → {DIMANCHE}')
    rel = gh_json('releases.json')
    known = {(e.get('sku') or '').upper() for e in rel} | {slug_of(e) for e in rel}
    wtc = {s: o for s, o in wtc_list(DIMANCHE, 6).items() if str(LUNDI) <= str(o['dropDate'])[:10] <= str(DIMANCHE)}
    print(f'  WTC : {len(wtc)} drops publics cette semaine')
    added, ret_added = [], 0
    with Retailers() as R:
        for s, o in sorted(wtc.items(), key=lambda x: x[1]['dropDate']):
            brand, why = eligible(o)
            if not brand: print(f"  ignoré ({why}) : {o.get('styleCode')} {o.get('brandName')}"); continue
            sku = (o.get('styleCode') or '').upper()
            if sku in known or s in known:
                e = next((x for x in rel if (x.get('sku') or '').upper() == sku or slug_of(x) == s), None)
                if e and (e.get('sku') or '').upper() not in LOCKED_SKUS:
                    n = merge_retailers(e, R.get(s, e.get('price')))
                    if n: ret_added += n; print(f"  + {n} retailer(s) → {sku} {e.get('title')}")
                continue
            if str(o['dropDate'])[:10] < str(TODAY): continue
            e = new_entry(o, brand); e['retailers'] = R.get(s, e['price']) or []
            localize_image(e); rel.append(e); added.append(e); known |= {sku, s}
            print(f"  + {e['date']} {sku} | {e['title']} | {e['price']}€ | img={'ok' if e['image_url'] else 'non'} | retailers={len(e['retailers'])}")
    rel.sort(key=sort_key)
    if added or ret_added:
        push_json('releases.json', rel, f'[skip ci] feat: semaine {LUNDI:%d/%m} — {len(added)} paire(s), {ret_added} retailer(s) WTC')
    # weekly_data.json = fiches releases.json de la semaine en cours
    wk_old = gh_json('weekly_data.json') or {}
    drops = sorted([dict(e) for e in rel if str(LUNDI) <= str(e.get('date', '')) <= str(DIMANCHE)], key=sort_key)
    label = f"{LUNDI.day}{'' if LUNDI.month == DIMANCHE.month else ' ' + MOIS[LUNDI.month - 1]} – {DIMANCHE.day} {MOIS[DIMANCHE.month - 1]} {DIMANCHE.year}"
    wk = {'week_start': str(LUNDI), 'week_end': str(DIMANCHE), 'label': label, 'drops': drops,
          'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}
    if json.dumps(wk_old.get('drops'), sort_keys=True) != json.dumps(drops, sort_keys=True) or wk_old.get('week_start') != str(LUNDI):
        push_json('weekly_data.json', wk, f'[skip ci] feat: weekly_data.json {label} ({len(drops)} drops)')
    print(f'RÉSUMÉ week : {len(added)} paire(s) ajoutée(s) {[e["sku"] for e in added]}, {ret_added} retailer(s) ajouté(s), weekly={len(drops)} drops')


def job_daily():
    print(f'[daily] {TODAY}')
    rel = gh_json('releases.json', 'perplexity')
    cur = gh_json('cursor.json', 'perplexity') or {'offset': 0}
    before = len(rel)
    rel = [r for r in rel if str(r.get('date', '')) in ('TBD', '?', '') or str(r.get('date', '')) >= str(LUNDI)]
    seen_s, seen_t, dedup = set(), set(), []
    for r in rel:
        s = (r.get('sku') or '').upper(); t = re.sub(r'\s+', ' ', (r.get('title') or '').lower().strip())
        if (s and s in seen_s) or (t and t in seen_t): continue
        if s: seen_s.add(s)
        if t: seen_t.add(t)
        dedup.append(r)
    rel = dedup; purged = before - len(rel)
    elig = [r for r in rel if r.get('wtc_url') and (r.get('sku') or '').upper() not in LOCKED_SKUS]
    off = cur.get('offset', 0) if cur.get('offset', 0) < len(elig) else 0
    batch = elig[off:off + 10]; nxt = off + 10 if off + 10 < len(elig) else 0
    changes, ret_added, missing = [], 0, 0
    with Retailers() as R:
        for e in batch:
            s = slug_of(e); d = wtc_detail(s)
            if d is None: missing += 1; continue
            if not e.get('retailers') and d:
                nd = str(d.get('dropDate') or '')[:10]
                if nd and d.get('isDropDateKnown') is not False and nd != e.get('date') and nd >= '2025-01-01':
                    changes.append(f"{e.get('sku')} date {e.get('date')}→{nd}"); e['date'] = nd
                    y, m, dd = nd.split('-'); e['date_display'] = f'{int(dd)} {MOIS[int(m) - 1]} {y}'
                p = d.get('retailPrice')
                if p and int(float(p)) != e.get('price'):
                    changes.append(f"{e.get('sku')} prix {e.get('price')}→{int(float(p))}"); e['price'] = int(float(p))
            n = merge_retailers(e, R.get(s, e.get('price')))
            if n: ret_added += n; changes.append(f"{e.get('sku')} +{n} retailer(s)")
    rel.sort(key=sort_key)
    if changes or purged:
        push_json('releases.json', rel, f'[skip ci] chore: daily lot {off // 10 + 1} ({len(changes)} changements, {purged} purgées)')
    if not DRY:
        cur['offset'] = nxt; gh_put('cursor.json', json.dumps(cur, indent=2).encode(), f'[skip ci] cursor: {nxt}', 'perplexity')
    print(f'RÉSUMÉ daily : lot {off}→{nxt} ({len(batch)} fiches, {missing} sans page WTC), {purged} purgée(s), changements={changes or "aucun"}')


def job_releases8():
    horizon = TODAY + timedelta(weeks=8)
    print(f'[releases8] {TODAY} → {horizon}')
    rel = gh_json('releases.json')
    known = {(e.get('sku') or '').upper() for e in rel} | {slug_of(e) for e in rel}
    wtc = {s: o for s, o in wtc_list(horizon).items() if str(TODAY) <= str(o['dropDate'])[:10] <= str(horizon)}
    print(f'  WTC : {len(wtc)} drops publics sur 8 semaines')
    added = []
    with Retailers() as R:
        for s, o in sorted(wtc.items(), key=lambda x: x[1]['dropDate']):
            sku = (o.get('styleCode') or '').upper()
            if sku in known or s in known: continue
            brand, why = eligible(o)
            if not brand: continue
            e = new_entry(o, brand); e['retailers'] = R.get(s, e['price']) or []
            localize_image(e); rel.append(e); added.append(e); known |= {sku, s}
            print(f"  + {e['date']} {sku} | {e['title']} | {e['price']}€ | img={'ok' if e['image_url'] else 'non'} | retailers={len(e['retailers'])}")
    if added:
        rel.sort(key=sort_key)
        push_json('releases.json', rel, f'[skip ci] feat: {len(added)} drop(s) des 8 prochaines semaines depuis WTC')
    print(f'RÉSUMÉ releases8 : {len(added)} paire(s) ajoutée(s) {[e["sku"] + " " + e["title"] for e in added]}')


def job_restocks():
    print(f'[restocks] {TODAY}')
    rs = gh_json('restocks.json')
    before = len(rs)
    keep = [r for r in rs if str(r.get('date', '')) in ('TBD', '') or str(r.get('date', '')) >= str(TODAY)]
    ret_added, changes = 0, []
    with Retailers() as R:
        for e in keep:
            s = slug_of(e)
            if not s: continue
            if not e.get('retailers'):
                d = wtc_detail(s) or {}
                nd = str(d.get('dropDate') or '')[:10]
                if nd and d.get('isDropDateKnown') is not False and nd != e.get('date'):
                    changes.append(f"{e.get('sku')} date {e.get('date')}→{nd}"); e['date'] = nd; e['date_display'] = nd
            n = merge_retailers(e, R.get(s, e.get('price')))
            if n: ret_added += n; changes.append(f"{e.get('sku')} +{n} retailer(s)")
            if n or changes: e['updated_at'] = str(TODAY)
    removed = before - len(keep)
    if removed or changes:
        keep.sort(key=sort_key)
        push_json('restocks.json', keep, f'[skip ci] chore: restocks — {removed} passé(s) retiré(s), {ret_added} retailer(s) ajouté(s)')
    print(f'RÉSUMÉ restocks : {len(keep)} restocks, {removed} passé(s) retiré(s), changements={changes or "aucun"}')


if __name__ == '__main__':
    jobs = {'week': job_week, 'daily': job_daily, 'releases8': job_releases8, 'restocks': job_restocks}
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args or args[0] not in jobs: print(__doc__); sys.exit(2)
    for a in args: jobs[a]()
