#!/usr/bin/env python3
"""
sneakernews_collector.py — Collecteur RSS Sneaker News
=======================================================
Ajoute dans releases.json les nouvelles paires depuis le flux RSS Sneaker News.
Utilise l'API GitHub (GET SHA frais → PUT) — JAMAIS de git local.

Usage (cron VPS, ex: toutes les 2h) :
    0 */2 * * * /usr/bin/python3 /var/www/sneakerdropfr/sneakernews_collector.py >> /var/log/sneakernews_collector.log 2>&1

Dépendances : aucune (stdlib uniquement)
"""

import json
import re
import time
import base64
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# ── Credentials ──────────────────────────────────────────────────────────────
import os
# Token GitHub : variable d'env GH_TOKEN (ou fallback hardcodé pour rétrocompat VPS)
GH_TOKEN = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN') or 'GHP_TOKEN_PLACEHOLDER'
REPO     = 'sneakerdropfr/sneakerdropfr.github.io'

# ── Constantes ────────────────────────────────────────────────────────────────
RSS_URL      = 'https://sneakernews.com/feed/'
MAX_NEW      = 10          # max nouvelles entrées par run
MAX_RETRIES  = 2           # retries sur conflit SHA 422/409

BANNED_SKUS  = {'KK2600', 'KK2599', 'KJ2419'}
BANNED_RETAILERS = {'stockx', 'goat', 'limited resell', 'klekt', 'restocks',
                    'laced', 'stadium goods', 'flight club', 'alias', 'bump'}
ALLOWED_BRANDS_LOW = {
    'nike', 'adidas', 'air jordan', 'jordan', 'new balance', 'puma',
    'vans', 'converse', 'reebok', 'asics', 'saucony', 'brooks', 'salomon'
}
BRAND_CANONICAL = {
    'nike': 'Nike', 'adidas': 'Adidas', 'air jordan': 'Air Jordan',
    'jordan': 'Jordan', 'new balance': 'New Balance', 'puma': 'Puma',
    'vans': 'Vans', 'converse': 'Converse', 'reebok': 'Reebok',
    'asics': 'ASICS', 'saucony': 'Saucony', 'brooks': 'Brooks', 'salomon': 'Salomon'
}
VALID_BRANDS = set(BRAND_CANONICAL.values())
CLOTHING_WORDS = {
    'hoodie', 'shirt', 'pants', 'tee', 'jacket', 'cap', 'hat', 'sock',
    'shorts', 'jersey', 'pant', 'sweater', 'fleece', 'vest', 'apparel',
    'collection', 'tracksuit', 'windbreaker', 'tights', 'legging',
    't-shirt', 'crop top', 'bra', 'skirt', 'dress', 'jeans'
}

# ── Nettoyage titres RSS ──────────────────────────────────────────────────────
RSS_VERBS = re.compile(
    r'\b(Releases?|Returns?|Drops?|Debuts?|Arrives?|Coming|Launching|Available|'
    r'Features?|Gets?|Reveals?|Unveiled|Restocks?|Links?|Adds?|Brings?|Goes?|'
    r'Slips?|Covers?|Recalls?|Mimics?|Crafts?|Gives?|Sees?|Takes?|Makes?|Puts?|'
    r'Sets?|Hits?|Lands?|Packs?|Looks?|Lends?|Keeps?|Turns?|Serves?|Offers?|'
    r'Winds?|Touts?|Docks?|Sharpens?|Checks?)\b', re.IGNORECASE)
RSS_PAST_VERBS = re.compile(
    r'\b(turned|dropped|released|debuted|unveiled|launched|arrived|returned|'
    r'restocked|revealed|featured|added|brought|slipped|covered|recalled|'
    r'mimicked|crafted|gave|saw|took|made|put|set|hit|landed|packed|looked|'
    r'kept|served|offered|laced|touted|beat)\b', re.IGNORECASE)
RSS_PHRASES = re.compile(
    r'(First Look|Where To Buy|Lock In:?|Official Images?|Release Date|How To Cop|'
    r'Buy Here|Detailed Look|On-Feet Look|Week \d+ Jawns?|Winds Down|Gives Off|'
    r'Checks Off|Sharpens "|The Shoe That|Releases On |Docks ")',
    re.IGNORECASE)
RSS_POSSESSIVE = re.compile(r"([\w][\w \t]{0,40}?)'s\b", re.UNICODE)

BRAND_MODELS = {
    'Air Jordan': ['1','2','3','4','5','6','7','8','9','10','11','12','13','14'],
    'Jordan': ['11','4','1'],
    'Nike': ['Air Force 1','Air Max 1','Air Max 90','Air Max 95','Air Max 97',
             'Air Max 270','Air Max Plus','Dunk Low','Dunk High','Dunk SB',
             'Blazer','Cortez','Pegasus','Vaporfly','React','Free Run',
             'Moon Shoe','Zoom Vomero','Waffle','KD','LeBron','Kobe',
             'Metcon','Mind 001','Mind 002','Skylon 11','P-6000','P6000','Air Force'],
    'New Balance': ['990v6','990v5','990v4','990v3','990v2','990','991v2','991',
                    '992','993','997','998','999','1906','2002R','2002','2010',
                    '574','530','327','550','725','740','860','580','1500','M990',
                    'FuelCell RC Elite','FuelCell','RC30'],
    'Adidas': ['Samba OG','Samba','Gazelle','Campus 00s','Campus','Stan Smith',
               'Handball Spezial','Ultraboost','NMD R1','NMD','Forum','Superstar',
               'Predator','Yeezy 350','Yeezy 700','Yeezy 500','Yeezy','ZX 8000','ZX'],
    'Puma':    ['Suede','Speedcat','Clyde'],
    'Vans':    ['Old Skool 36','Old Skool','Sk8-Hi','Era','Authentic','Slip-On'],
    'Converse':['Chuck 70','Chuck Taylor','All Star','Run Star Hike'],
    'Reebok':  ['Classic Leather','Club C','Freestyle','Pump Fury','Pump'],
    'Asics':   ['Gel-Lyte III','Gel-Lyte','Gel-Nimbus','Gel-Kayano','GT-2160','GT-2000'],
    'Saucony': ['Jazz Original','Jazz','Shadow 6000','Shadow 5000','Shadow','Grid 9000','Ride'],
    'Brooks':  ['Adrenaline GTS 10','Adrenaline GTS','Ghost'],
    'Salomon': ['XT-6','Speedcross 3','Speedcross','Advanced'],
}
COLLAB_BRANDS = re.compile(
    r'\b(DTLR|Bodega|SNS|Concepts|Slam Jam|Stussy|Palace|Supreme|Off-White|'
    r'Travis Scott|Fear of God|Union|Fragment|Atmos|Patta|Kith|Extra Butter|'
    r'West NYC|JJJJound|Aim[eé] Leon Dore|ALD|Afew|Brain Dead|Cactus Plant|CLOT|'
    r'Dover Street|DSM|END|Mita|Offspring|Packer|Ronnie Fieg|Social Status|'
    r'Trophy Room|Undefeated|UNDFTD|DISTANCE|SKIMS|Simone Rocha|Cecilie Bahnsen|'
    r'Arte Antwerp|Sydney Levrone|Action Bronson|Travis Scott)\b', re.IGNORECASE)
NOISE_WORDS = re.compile(
    r'\b(The|A|An|In|On|With|To|At|Of|And|Or|For|By|As|Its?|Their|This|That|'
    r'These|Those|New|Popular|Tech|Runners?|Sneakers?|Brand|Colorway|'
    r'August|July|June|May|April|March|January|February|September|October|'
    r'November|December|\d{1,2}(?:st|nd|rd|th)?|20\d{2}|Week)\b', re.IGNORECASE)

# ── Fonctions nettoyage titre ─────────────────────────────────────────────────

def is_rss_title(title: str) -> bool:
    t = str(title or '')
    return (
        len(t.split()) > 6
        or bool(RSS_VERBS.search(t))
        or bool(RSS_PAST_VERBS.search(t))
        or bool(RSS_PHRASES.search(t))
        or bool(RSS_POSSESSIVE.search(t))
    )

def clean_rss_title(title: str) -> str:
    """Reformule un titre RSS → 'Marque Modèle Colorway'. Conserve si marque/modèle non identifiables."""
    t = str(title or '').strip()
    if not is_rss_title(t):
        return t
    t_clean = RSS_POSSESSIVE.sub(lambda m: m.group(1).strip(), t)
    found_brand = found_model = collab = None
    for brand, models in BRAND_MODELS.items():
        if re.search(r'\b' + re.escape(brand) + r'\b', t_clean, re.IGNORECASE):
            for model in sorted(models, key=len, reverse=True):
                if re.search(re.escape(model), t_clean, re.IGNORECASE):
                    found_brand = brand
                    found_model = model
                    break
            if found_brand:
                break
    if not found_brand or not found_model:
        return t
    cm = COLLAB_BRANDS.search(t_clean)
    if cm:
        collab = cm.group(0)
        if re.match(r'aim[eé]\s+leon\s+dore', collab, re.IGNORECASE):
            collab = 'Aimé Leon Dore'
    stripped = t_clean
    if collab:
        stripped = re.sub(r'\b' + re.escape(collab) + r'\b', ' ', stripped, flags=re.IGNORECASE)
    stripped = re.sub(r'\b' + re.escape(found_brand) + r'\b', ' ', stripped, flags=re.IGNORECASE)
    if found_brand == 'Air Jordan':
        stripped = re.sub(r'\bJordan\b', ' ', stripped, flags=re.IGNORECASE)
    if found_brand == 'New Balance':
        stripped = re.sub(r'\bBalance\b', ' ', stripped, flags=re.IGNORECASE)
    stripped = re.sub(re.escape(found_model), ' ', stripped, flags=re.IGNORECASE)
    for token in found_model.split():
        if len(token) >= 2 and not token.isdigit():
            stripped = re.sub(r'\b' + re.escape(token) + r'\b', ' ', stripped, flags=re.IGNORECASE)
    stripped = RSS_VERBS.sub(' ', stripped)
    stripped = RSS_PAST_VERBS.sub(' ', stripped)
    stripped = RSS_PHRASES.sub(' ', stripped)
    stripped = NOISE_WORDS.sub(' ', stripped)
    stripped = re.sub(r"'s?\b", ' ', stripped)
    stripped = re.sub(r'\s*\bx\b\s*', ' ', stripped, flags=re.IGNORECASE)
    stripped = re.sub(r'\s+', ' ', stripped).strip(' -\u2013\u2014,./x')
    stripped = re.sub(r'^x\s+|^x$|\s+x$', '', stripped, flags=re.IGNORECASE).strip()
    prefix = f'{collab} x {found_brand}' if collab else found_brand
    parts = [prefix, found_model]
    if stripped and len(stripped) >= 2:
        parts.append(stripped)
    result = ' '.join(p for p in parts if p)
    return result if len(result) < len(t) else t

def detect_brand(title: str) -> str:
    """Détecte la marque principale dans un titre RSS."""
    tl = title.lower()
    for key, val in sorted(BRAND_CANONICAL.items(), key=lambda x: -len(x[0])):
        if re.search(r'\b' + re.escape(key) + r'\b', tl):
            return val
    return ''

def is_rss_brut(title: str) -> bool:
    """Retourne True si le titre est clairement un titre RSS non nettoyable."""
    return bool(RSS_PHRASES.search(title)) and not detect_brand(title)

# ── Helpers GitHub API ────────────────────────────────────────────────────────

def gh_get(file: str, branch: str = 'main'):
    req = urllib.request.Request(
        f'https://api.github.com/repos/{REPO}/contents/{file}?ref={branch}',
        headers={'Authorization': f'token {GH_TOKEN}', 'Accept': 'application/vnd.github.v3+json'})
    with urllib.request.urlopen(req, timeout=15) as r:
        meta = json.loads(r.read())
    return json.loads(base64.b64decode(meta['content']).decode()), meta['sha']

def gh_put(file: str, data: list, sha: str, message: str, branch: str) -> str:
    """PUT avec retry automatique sur conflit SHA 409/422."""
    for attempt in range(MAX_RETRIES):
        content_b64 = base64.b64encode(
            json.dumps(data, ensure_ascii=False, indent=2).encode()
        ).decode()
        body = json.dumps({
            'message': message,
            'content': content_b64,
            'sha': sha,
            'branch': branch
        }).encode()
        req = urllib.request.Request(
            f'https://api.github.com/repos/{REPO}/contents/{file}',
            data=body, method='PUT',
            headers={
                'Authorization': f'token {GH_TOKEN}',
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            })
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())['content']['sha'][:8]
        except urllib.error.HTTPError as e:
            if e.code in (409, 422) and attempt < MAX_RETRIES - 1:
                print(f'  ⚠ Conflit SHA {e.code} sur {branch}, re-GET SHA frais (tentative {attempt+2})...')
                time.sleep(2)
                _, sha = gh_get(file, branch)  # SHA frais
                continue
            raise
    raise RuntimeError(f'gh_put échoué après {MAX_RETRIES} tentatives')

# ── Fetch RSS Sneaker News ────────────────────────────────────────────────────

def fetch_rss(url: str) -> list[dict]:
    """Retourne la liste des items du flux RSS sous forme de dicts."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        xml_data = r.read()
    root = ET.fromstring(xml_data)
    items = []
    ns = {'media': 'http://search.yahoo.com/mrss/'}
    for item in root.findall('.//item'):
        def tag(name):
            el = item.find(name)
            return el.text.strip() if el is not None and el.text else ''
        title_raw = tag('title')
        link      = tag('link')
        pub_date  = tag('pubDate')
        # Image : media:content ou enclosure
        img = ''
        mc = item.find('media:content', ns)
        if mc is not None:
            img = mc.get('url', '')
        if not img:
            enc = item.find('enclosure')
            if enc is not None:
                img = enc.get('url', '')
        # SKU depuis URL ou titre
        sku = ''
        sku_m = re.search(r'\b([A-Z]{1,3}[0-9]{4,6}(?:-[0-9]{3})?|[A-Z]{2}[0-9]{4}[A-Z]?)\b',
                          link + ' ' + title_raw)
        if sku_m:
            sku = sku_m.group(1).upper()
        items.append({
            'title_raw': title_raw,
            'link': link,
            'pub_date': pub_date,
            'img': img,
            'sku': sku,
        })
    return items

# ── Purge et dédup pre-push ───────────────────────────────────────────────────

def purge_and_dedup(releases: list, lundi_semaine: str) -> list:
    """
    Purge les entrées date < lundi_semaine (sauf TBD/vides).
    Déduplique par SKU et titre normalisé.
    NE SUPPRIME JAMAIS les entrées futures (date > today).
    """
    cleaned = [r for r in releases
               if r.get('date', '') in ('TBD', '?', '')
               or r.get('date', '') >= lundi_semaine]
    seen_skus  = set()
    seen_titles = set()
    deduped = []
    for r in cleaned:
        sku   = (r.get('sku', '') or '').upper()
        title = re.sub(r'\s+', ' ', (r.get('title', '') or '').lower().strip())
        if sku and sku in seen_skus:
            continue
        if title in seen_titles:
            continue
        if sku:
            seen_skus.add(sku)
        seen_titles.add(title)
        deduped.append(r)
    return deduped

# ── Pipeline principal ────────────────────────────────────────────────────────

def main():
    now = datetime.now(timezone.utc)
    today = now.date()
    lundi_semaine = str(today - __import__('datetime').timedelta(days=today.weekday()))
    print(f'[{now.isoformat()}] sneakernews_collector — démarrage')

    # 1. Lire releases.json sur les deux branches (SHA frais)
    releases_main, sha_main       = gh_get('releases.json', 'main')
    releases_perp, sha_perp       = gh_get('releases.json', 'perplexity')

    # Utiliser main comme base (plus récent après run RSS)
    releases = releases_main

    # Index existants
    existing_skus   = {(r.get('sku', '') or '').upper() for r in releases if r.get('sku')}
    existing_slugs  = {r.get('slug', '') for r in releases}
    existing_ids    = {r.get('id', '') for r in releases}
    existing_titles = {re.sub(r'\s+', ' ', (r.get('title', '') or '').lower().strip()) for r in releases}

    # 2. Fetch RSS
    try:
        rss_items = fetch_rss(RSS_URL)
        print(f'  RSS: {len(rss_items)} items récupérés')
    except Exception as e:
        print(f'  ⚠ Erreur RSS: {e}')
        return

    # 3. Filtrer et construire les nouvelles entrées
    new_entries = []
    for item in rss_items:
        if len(new_entries) >= MAX_NEW:
            break
        title_raw = item['title_raw']
        sku       = item['sku'].upper()
        link      = item['link']
        img_url   = item['img']

        # Filtre SKU banni
        if sku and sku in BANNED_SKUS:
            continue

        # Détecter la marque
        brand = detect_brand(title_raw)
        if not brand:
            continue  # marque non reconnue → skip

        # Filtre vêtements
        if any(w in title_raw.lower() for w in CLOTHING_WORDS):
            continue

        # Nettoyer le titre
        title_clean = clean_rss_title(title_raw)

        # Filtre titres RSS bruts non nettoyables (aucun modèle identifiable)
        if is_rss_brut(title_clean):
            print(f'  SKIP (RSS brut non nettoyable): {title_raw[:60]}')
            continue

        # Construire l'ID slug
        entry_id = re.sub(r'[^a-z0-9-]', '-', title_clean.lower()) + '-' + sku.lower()
        entry_id = re.sub(r'-+', '-', entry_id).strip('-')[:80]

        # Déduplication
        title_norm = re.sub(r'\s+', ' ', title_clean.lower().strip())
        if sku and sku in existing_skus:
            continue
        if entry_id in existing_ids:
            continue
        if title_norm in existing_titles:
            continue

        # Image : NE PAS utiliser sneakernews.com directement
        # → on laisse vide (sera remplie par le cron 17de7fe5 via WTC)
        image_url = ''
        if img_url and 'sneakernews.com' not in img_url:
            image_url = img_url

        entry = {
            'id': entry_id,
            'slug': entry_id,
            'title': title_clean,
            'brand': brand,
            'date': 'TBD',
            'price': 0,
            'sku': sku,
            'image_url': image_url,
            'source': 'Sneaker News',
            'buy_url': link,
            'wtc_url': f'https://www.whentocop.fr/drops/{entry_id}',
            'retailers': [],
            'featured': False,
            'added_at': now.isoformat(),
        }
        new_entries.append(entry)
        existing_skus.add(sku)
        existing_ids.add(entry_id)
        existing_titles.add(title_norm)
        print(f'  + {brand} | {title_clean[:50]}  [{sku}]')

    if not new_entries:
        print('  Aucune nouvelle paire à ajouter.')
        return

    print(f'  → {len(new_entries)} nouvelle(s) paire(s) à ajouter')

    # 4. Ajouter au début (les plus récentes en premier) + purger + dédupliquer
    releases = new_entries + releases
    releases = purge_and_dedup(releases, lundi_semaine)

    # 5. Push sur perplexity ET main avec retry SHA
    msg = f'[skip ci] feat: {len(new_entries)} nouvelle(s) sortie(s) depuis Sneaker News RSS'

    # Push perplexity (SHA frais)
    _, sha_perp = gh_get('releases.json', 'perplexity')
    sha_p = gh_put('releases.json', releases, sha_perp, msg, 'perplexity')
    print(f'  Push perplexity: {sha_p}')

    # Push main (SHA frais)
    _, sha_main = gh_get('releases.json', 'main')
    sha_m = gh_put('releases.json', releases, sha_main, msg, 'main')
    print(f'  Push main: {sha_m}')

    print(f'[OK] {len(new_entries)} nouvelles paires ajoutées | {len(releases)} entrées total')


if __name__ == '__main__':
    main()
