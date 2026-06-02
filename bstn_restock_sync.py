#!/usr/bin/env python3
"""
bstn_restock_sync.py
====================
Détection automatique de restocks BSTN via le flux Awin.

Fonctionnement :
  1. Télécharge le feed BSTN FR (FID 99343) depuis Awin
  2. Pour chaque produit en stock, extrait le SKU (colonne mpn)
  3. Cherche ce SKU dans releases_past.json ET releases.json
  4. Si trouvé ET aucun restock BSTN pour la date d'aujourd'hui → injecte le restock
  5. Sauvegarde releases_past.json et releases.json mis à jour
  6. Push sur GitHub

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
import urllib.request
import urllib.error
from datetime import date, datetime

# ── Configuration ────────────────────────────────────────────────────────────

AWIN_API_KEY    = "3030aadc2e758542061a28ab8d8e68a3"
BSTN_FEED_FID   = "99343"
AWIN_AFFID      = "2855487"

FEED_URL = (
    f"https://productdata.awin.com/datafeed/download/apikey/{AWIN_API_KEY}"
    f"/fid/{BSTN_FEED_FID}/format/csv/language/fr/delimiter/%2C/compression/gzip"
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

SCRIPT_DIR        = os.path.dirname(os.path.abspath(__file__))
RELEASES_PAST     = os.path.join(SCRIPT_DIR, "releases_past.json")
RELEASES_ACTIVE   = os.path.join(SCRIPT_DIR, "releases.json")

TODAY = date.today().isoformat()  # "YYYY-MM-DD"

# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


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
    Parse le feed gzip CSV et retourne un dict {SKU_UPPER: first_row_in_stock}.
    On garde un seul produit par SKU (le premier rencontré en stock).
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
                continue  # garder seulement le premier

            sku_map[mpn] = {
                'product_name': row.get('product_name', '').strip(),
                'aw_deep_link': row.get('aw_deep_link', '').strip(),
                'search_price': row.get('search_price', '').strip(),
                'currency': row.get('currency', 'EUR').strip(),
            }

    log(f"SKUs en stock dans le feed : {len(sku_map)}")
    return sku_map


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def format_price(price_str, currency):
    """Formater le prix : "189.99" + "EUR" → "190€"."""
    try:
        val = float(price_str)
        symbol = "€" if currency in ("EUR", "") else currency
        # Arrondir si .00, sinon garder 2 décimales
        if val == int(val):
            return f"{int(val)}{symbol}"
        else:
            return f"{val:.2f}{symbol}".replace(".", ",")
    except (ValueError, TypeError):
        return f"{price_str}€"


def already_has_bstn_restock(restocks, today):
    """Retourne True si un restock BSTN existe déjà pour la date today."""
    for rs in restocks:
        if rs.get('date') != today:
            continue
        for retailer in rs.get('retailers', []):
            if retailer.get('name') == 'BSTN':
                return True
    return False


def inject_restocks(releases, feed_sku_map, source_label):
    """
    Parcourt une liste de releases, injecte les restocks BSTN si nécessaire.
    Retourne (releases_modifiées, nb_injections).
    """
    injected = 0

    for r in releases:
        sku = r.get('sku', '').strip().upper()
        if not sku:
            continue
        if sku not in feed_sku_map:
            continue

        feed_entry = feed_sku_map[sku]

        # Initialiser restocks si absent
        if 'restocks' not in r:
            r['restocks'] = []

        # Anti-doublon : déjà un restock BSTN aujourd'hui ?
        if already_has_bstn_restock(r['restocks'], TODAY):
            log(f"  SKIP (doublon) : {r.get('id')} — BSTN restock déjà enregistré le {TODAY}")
            continue

        # Construire l'entrée restock
        price_str = format_price(feed_entry['search_price'], feed_entry.get('currency', 'EUR'))
        restock_entry = {
            "date": TODAY,
            "retailers": [
                {
                    "name": "BSTN",
                    "url": feed_entry['aw_deep_link'],
                    "price": price_str
                }
            ]
        }

        r['restocks'].append(restock_entry)
        injected += 1
        log(f"  ✓ Restock injecté [{source_label}] : {r.get('title', r.get('id'))} — {price_str}")

    return releases, injected


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log("=== bstn_restock_sync.py démarré ===")
    log(f"Date du jour : {TODAY}")

    # 1. Télécharger et parser le feed
    gz_data = download_feed()
    feed_sku_map = parse_feed(gz_data)

    if not feed_sku_map:
        log("ERREUR : feed vide ou inaccessible. Abandon.")
        sys.exit(1)

    # 2. Charger les releases
    log("Chargement releases_past.json...")
    releases_past = load_json(RELEASES_PAST)
    log("Chargement releases.json...")
    releases_active = load_json(RELEASES_ACTIVE)

    # 3. Injecter les restocks
    log("--- Injection restocks releases_past.json ---")
    releases_past, n_past = inject_restocks(releases_past, feed_sku_map, "past")

    log("--- Injection restocks releases.json ---")
    releases_active, n_active = inject_restocks(releases_active, feed_sku_map, "active")

    total = n_past + n_active
    log(f"Total restocks injectés : {total} (past={n_past}, active={n_active})")

    if total == 0:
        log("Aucun nouveau restock détecté. Pas de commit nécessaire.")
        return

    # 4. Sauvegarder les JSON
    log("Sauvegarde releases_past.json...")
    save_json(RELEASES_PAST, releases_past)

    log("Sauvegarde releases.json...")
    save_json(RELEASES_ACTIVE, releases_active)

    # 5. Régénérer les pages HTML des releases concernées
    log("Régénération pages HTML des releases avec nouveaux restocks...")
    _regenerate_pages(releases_past, releases_active)

    # 6. Git commit + push
    log("Commit + push GitHub...")
    _git_push(total)

    log("=== bstn_restock_sync.py terminé avec succès ===")


def _regenerate_pages(releases_past, releases_active):
    """Régénère les pages HTML des releases ayant des restocks BSTN injectés aujourd'hui."""
    import subprocess, sys

    # Importer generate_release_pages depuis le même dossier
    sys.path.insert(0, SCRIPT_DIR)
    try:
        import importlib
        grp = importlib.import_module("generate_release_pages")
    except ImportError as e:
        log(f"WARN : impossible d'importer generate_release_pages : {e}")
        return

    all_releases = releases_past + releases_active
    sorties_dir = os.path.join(SCRIPT_DIR, "sorties")
    os.makedirs(sorties_dir, exist_ok=True)

    regenerated = 0
    for r in all_releases:
        # Vérifier si ce release a un restock injecté aujourd'hui
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
            log(f"  Page régénérée : {release_id}.html")
            regenerated += 1
        except Exception as e:
            log(f"  WARN : échec régénération {release_id} : {e}")

    log(f"Pages régénérées : {regenerated}")


def _git_push(nb_restocks):
    """Commit et push les modifications sur GitHub."""
    import subprocess

    def run(cmd, **kwargs):
        result = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True, **kwargs)
        if result.returncode != 0:
            log(f"  git stderr: {result.stderr.strip()}")
        return result

    run(["git", "config", "user.email", "melakh@hotmail.com"])
    run(["git", "config", "user.name", "SneakerDropFR Bot"])

    # Ajouter tous les fichiers modifiés
    run(["git", "add", "releases_past.json", "releases.json"])
    # Ajouter les pages HTML régénérées
    run(["git", "add", "sorties/"])

    commit_msg = f"restock: injection automatique BSTN — {nb_restocks} restock(s) le {TODAY}"
    result = run(["git", "commit", "-m", commit_msg])

    if "nothing to commit" in result.stdout + result.stderr:
        log("Git : rien à commiter.")
        return

    push = run(["git", "push"])
    if push.returncode == 0:
        log(f"Push réussi : {commit_msg}")
    else:
        log(f"ERREUR push : {push.stderr.strip()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
