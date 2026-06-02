#!/usr/bin/env python3
"""
bstn_restock_sync.py — Version VPS standalone
===============================================
À placer dans /root/ sur le VPS.
Tourne via cron : 0 9,19 * * * /usr/bin/python3 /root/bstn_restock_sync.py >> /var/log/bstn_restock.log 2>&1

Fonctionnement :
  1. Télécharge le feed BSTN FR (FID 99343) depuis Awin
  2. Pour chaque produit en stock, extrait le SKU (colonne mpn)
  3. Lit releases_past.json ET releases.json depuis le repo GitHub via l'API
  4. Si SKU trouvé ET pas de restock BSTN pour aujourd'hui → injecte le restock
  5. Push les JSON modifiés sur GitHub via l'API
  6. Régénère + push les pages HTML via generate_release_pages.py (si dispo)

Format injecté :
  {"date": "YYYY-MM-DD", "retailers": [{"name": "BSTN", "url": "https://awin...", "price": "XXX€"}]}

Règle anti-doublon : pas de doublon si un restock BSTN existe déjà pour la même date.
"""

import json
import gzip
import csv
import io
import os
import sys
import base64
import subprocess
import urllib.request
import urllib.error
from datetime import date, datetime

# ── Configuration ────────────────────────────────────────────────────────────

AWIN_API_KEY  = "3030aadc2e758542061a28ab8d8e68a3"
BSTN_FEED_FID = "99343"
AWIN_AFFID    = "2855487"

# Token GitHub — à définir en variable d'environnement sur le VPS :
# export GITHUB_TOKEN="ghp_xxx..."  (dans /root/.bashrc ou le crontab)
GITHUB_TOKEN  = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO   = "sneakerdropfr/sneakerdropfr.github.io"
GITHUB_BRANCH = "main"

# Chemin local du repo cloné sur le VPS (pour régénération HTML)
# Mettre None si le repo n'est pas cloné localement
REPO_LOCAL_PATH = "/root/sneakerdropfr.github.io"

TODAY = date.today().isoformat()  # "YYYY-MM-DD"

FEED_URL = (
    "https://productdata.awin.com/datafeed/download/apikey/" + AWIN_API_KEY +
    "/fid/" + BSTN_FEED_FID + "/format/csv/language/fr/delimiter/%2C/compression/gzip"
    "/columns/data_feed_id%2Cmerchant_id%2Cmerchant_name%2Caw_product_id"
    "%2Caw_deep_link%2Caw_image_url%2Caw_thumb_url%2Ccategory_id%2Ccategory_name"
    "%2Cbrand_id%2Cbrand_name%2Cmerchant_product_id%2Cmerchant_category%2Cean"
    "%2Cmpn%2Cisbn%2Cmodel_number%2Cproduct_name%2Cdescription%2Cspecifications"
    "%2Clanguage%2Cmerchant_deep_link%2Cmerchant_thumb_url%2Cmerchant_image_url"
    "%2Cdelivery_time%2Cvalid_from%2Cvalid_to%2Ccurrency%2Csearch_price%2Cstore_price"
    "%2Cdelivery_cost%2Cweb_offer%2Cpre_order%2Cin_stock%2Cstock_quantity%2Cwarranty"
    "%2Ccondition%2Cparent_product_id%2Ccommission_group%2Clast_updated%2Cdimensions"
    "%2Ccolour%2Ckeywords%2Ccustom_1%2Ccustom_2%2Ccustom_3%2Ccustom_4%2Ccustom_5"
    "%2Csaving%2CFashion%3Asuitable_for%2CFashion%3Asize%2CFashion%3Amaterial"
    "%2CFashion%3Apattern%2CFashion%3Aswatch%2Crating%2Calternate_image%2Clarge_image"
    "%2Cbasket_link%2Cproduct_short_description%2Cmerchant_product_category_path"
    "%2Cmerchant_product_second_category%2Cmerchant_product_third_category"
    "%2Csavings_percent%2Cproduct_price_old%2Calternate_image_two%2Calternate_image_three"
    "%2Calternate_image_four/"
)

# ── Logging ───────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

# ── GitHub API ────────────────────────────────────────────────────────────────

def github_api(method, path, body=None):
    """Appel API GitHub REST."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "SneakerDropFR-ReStock/1.0",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        log(f"GitHub API error {e.code}: {e.read().decode()[:200]}")
        raise


def github_get_file(filepath):
    """Récupère le contenu + SHA d'un fichier depuis GitHub."""
    data = github_api("GET", f"contents/{filepath}?ref={GITHUB_BRANCH}")
    content = base64.b64decode(data["content"]).decode("utf-8")
    sha = data["sha"]
    return json.loads(content), sha


def github_put_file(filepath, content_str, sha, commit_message):
    """Met à jour un fichier sur GitHub via l'API."""
    encoded = base64.b64encode(content_str.encode("utf-8")).decode("ascii")
    body = {
        "message": commit_message,
        "content": encoded,
        "sha": sha,
        "branch": GITHUB_BRANCH,
        "committer": {
            "name": "SneakerDropFR Bot",
            "email": "melakh@hotmail.com"
        }
    }
    return github_api("PUT", f"contents/{filepath}", body)

# ── Feed BSTN ─────────────────────────────────────────────────────────────────

def download_feed():
    """Télécharge et retourne le contenu gzip du feed BSTN."""
    log(f"Téléchargement feed BSTN (FID {BSTN_FEED_FID})...")
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "SneakerDropFR/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    log(f"Feed téléchargé ({len(data)/1024/1024:.1f} MB gzippé)")
    return data


def parse_feed(gz_data):
    """
    Parse le feed gzip CSV.
    Retourne dict {SKU_UPPER: {product_name, aw_deep_link, search_price, currency}}.
    Un seul produit par SKU (premier en stock).
    """
    log("Parsing feed BSTN...")
    sku_map = {}

    with gzip.open(io.BytesIO(gz_data), 'rt', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mpn = row.get('mpn', '').strip().upper()
            in_stock = row.get('in_stock', '').strip()
            if not mpn or in_stock != '1':
                continue
            if mpn in sku_map:
                continue
            sku_map[mpn] = {
                'product_name': row.get('product_name', '').strip(),
                'aw_deep_link': row.get('aw_deep_link', '').strip(),
                'search_price': row.get('search_price', '').strip(),
                'currency': row.get('currency', 'EUR').strip(),
            }

    log(f"SKUs en stock dans le feed : {len(sku_map)}")
    return sku_map

# ── Helpers ───────────────────────────────────────────────────────────────────

def format_price(price_str, currency):
    """'189.99' + 'EUR' → '190€'  /  '189.50' → '189,50€'"""
    try:
        val = float(price_str)
        symbol = "€" if currency in ("EUR", "") else currency
        if val == int(val):
            return f"{int(val)}{symbol}"
        else:
            return f"{val:.2f}{symbol}".replace(".", ",")
    except (ValueError, TypeError):
        return f"{price_str}€"


def already_has_bstn_restock(restocks, today):
    """True si un restock BSTN existe déjà pour la date today."""
    for rs in restocks:
        if rs.get('date') != today:
            continue
        for retailer in rs.get('retailers', []):
            if retailer.get('name') == 'BSTN':
                return True
    return False


def inject_restocks(releases, feed_sku_map, source_label):
    """Injecte les restocks BSTN. Retourne (releases, nb_injections)."""
    injected = 0
    for r in releases:
        sku = r.get('sku', '').strip().upper()
        if not sku or sku not in feed_sku_map:
            continue
        feed_entry = feed_sku_map[sku]
        if 'restocks' not in r:
            r['restocks'] = []
        if already_has_bstn_restock(r['restocks'], TODAY):
            log(f"  SKIP (doublon) : {r.get('id')} — restock BSTN déjà enregistré le {TODAY}")
            continue
        price_str = format_price(feed_entry['search_price'], feed_entry.get('currency', 'EUR'))
        r['restocks'].append({
            "date": TODAY,
            "retailers": [{
                "name": "BSTN",
                "url": feed_entry['aw_deep_link'],
                "price": price_str
            }]
        })
        injected += 1
        log(f"  ✓ [{source_label}] {r.get('title', r.get('id'))} — {price_str}")
    return releases, injected

# ── Régénération HTML (si repo cloné localement) ─────────────────────────────

def regenerate_and_push_html(all_releases, releases_past, releases_active):
    """
    Si le repo est cloné en local, régénère les pages HTML des releases
    ayant un restock BSTN injecté aujourd'hui, puis git push.
    """
    if not REPO_LOCAL_PATH or not os.path.isdir(REPO_LOCAL_PATH):
        log("Repo local non disponible — skip régénération HTML")
        return

    sys.path.insert(0, REPO_LOCAL_PATH)
    try:
        import importlib
        grp = importlib.import_module("generate_release_pages")
    except ImportError as e:
        log(f"WARN : impossible d'importer generate_release_pages : {e}")
        return

    sorties_dir = os.path.join(REPO_LOCAL_PATH, "sorties")
    os.makedirs(sorties_dir, exist_ok=True)

    # Écrire les JSON mis à jour dans le repo local
    past_path   = os.path.join(REPO_LOCAL_PATH, "releases_past.json")
    active_path = os.path.join(REPO_LOCAL_PATH, "releases.json")
    with open(past_path, 'w', encoding='utf-8') as f:
        json.dump(releases_past, f, ensure_ascii=False, indent=2)
    with open(active_path, 'w', encoding='utf-8') as f:
        json.dump(releases_active, f, ensure_ascii=False, indent=2)

    regenerated = 0
    for r in all_releases:
        has_today = any(
            rs.get('date') == TODAY and
            any(ret.get('name') == 'BSTN' for ret in rs.get('retailers', []))
            for rs in r.get('restocks', [])
        )
        if not has_today:
            continue
        release_id = r.get('id', '')
        if not release_id:
            continue
        try:
            html = grp.render_page(r, all_releases)
            out_path = os.path.join(sorties_dir, f"{release_id}.html")
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(html)
            regenerated += 1
        except Exception as e:
            log(f"  WARN régénération {release_id} : {e}")

    log(f"Pages HTML régénérées : {regenerated}")

    if regenerated == 0:
        return

    # Git commit + push depuis le repo local
    def run(cmd):
        return subprocess.run(cmd, cwd=REPO_LOCAL_PATH, capture_output=True, text=True)

    run(["git", "config", "user.email", "melakh@hotmail.com"])
    run(["git", "config", "user.name", "SneakerDropFR Bot"])
    run(["git", "add", "releases_past.json", "releases.json", "sorties/"])
    result = run(["git", "commit", "-m",
                  f"restock: régénération HTML BSTN — {regenerated} pages le {TODAY}"])
    if "nothing to commit" in result.stdout + result.stderr:
        log("Git : rien à committer pour les HTML.")
        return
    push = run(["git", "push"])
    if push.returncode == 0:
        log(f"Git push HTML réussi.")
    else:
        log(f"WARN git push HTML : {push.stderr.strip()}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log("=" * 60)
    log("bstn_restock_sync.py démarré")
    log(f"Date du jour : {TODAY}")

    # 1. Télécharger + parser le feed Awin BSTN
    try:
        gz_data = download_feed()
    except Exception as e:
        log(f"ERREUR téléchargement feed : {e}")
        sys.exit(1)

    feed_sku_map = parse_feed(gz_data)
    if not feed_sku_map:
        log("ERREUR : feed vide ou inaccessible. Abandon.")
        sys.exit(1)

    # 2. Lire les releases depuis GitHub API
    log("Lecture releases_past.json depuis GitHub...")
    try:
        releases_past, sha_past = github_get_file("releases_past.json")
    except Exception as e:
        log(f"ERREUR lecture releases_past.json : {e}")
        sys.exit(1)

    log("Lecture releases.json depuis GitHub...")
    try:
        releases_active, sha_active = github_get_file("releases.json")
    except Exception as e:
        log(f"ERREUR lecture releases.json : {e}")
        sys.exit(1)

    # 3. Injecter les restocks
    log("--- Injection restocks releases_past.json ---")
    releases_past, n_past = inject_restocks(releases_past, feed_sku_map, "past")

    log("--- Injection restocks releases.json ---")
    releases_active, n_active = inject_restocks(releases_active, feed_sku_map, "active")

    total = n_past + n_active
    log(f"Total restocks injectés : {total} (past={n_past}, active={n_active})")

    if total == 0:
        log("Aucun nouveau restock détecté. Rien à pusher.")
        log("=" * 60)
        return

    # 4. Push releases_past.json sur GitHub
    if n_past > 0:
        log("Push releases_past.json → GitHub...")
        try:
            github_put_file(
                "releases_past.json",
                json.dumps(releases_past, ensure_ascii=False, indent=2),
                sha_past,
                f"restock: {n_past} restock(s) BSTN injecté(s) dans releases_past — {TODAY}"
            )
            log("releases_past.json pushé.")
        except Exception as e:
            log(f"ERREUR push releases_past.json : {e}")
            sys.exit(1)

    # 5. Push releases.json sur GitHub
    if n_active > 0:
        log("Push releases.json → GitHub...")
        try:
            # Relire le SHA après le push précédent si les deux fichiers ont changé
            _, sha_active_fresh = github_get_file("releases.json")
            github_put_file(
                "releases.json",
                json.dumps(releases_active, ensure_ascii=False, indent=2),
                sha_active_fresh,
                f"restock: {n_active} restock(s) BSTN injecté(s) dans releases — {TODAY}"
            )
            log("releases.json pushé.")
        except Exception as e:
            log(f"ERREUR push releases.json : {e}")
            sys.exit(1)

    # 6. Régénération HTML (si repo cloné localement)
    all_releases = releases_past + releases_active
    regenerate_and_push_html(all_releases, releases_past, releases_active)

    log(f"Terminé — {total} restock(s) BSTN enregistré(s) le {TODAY}.")
    log("=" * 60)


if __name__ == "__main__":
    main()
