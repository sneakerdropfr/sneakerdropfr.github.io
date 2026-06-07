#!/usr/bin/env python3
"""
snipes_solebox_sync.py
Surveillance quotidienne Snipes FR + Solebox — injection retailers dans releases.json
Auteur : SneakerDropFR
Crontab VPS : 0 6,18 * * * /usr/bin/python3 /root/snipes_solebox_sync.py >> /var/log/snipes_sync.log 2>&1
"""

import json
import time
import urllib.parse
import urllib.request
import urllib.error
import re
import base64
import logging
from datetime import datetime, timezone

# ── CONFIG ──────────────────────────────────────────────────────────────────
GH_TOKEN = open('/etc/environment').read().split('GH_TOKEN=')[1].split('\n')[0].strip().strip('"')
GH_REPO    = "sneakerdropfr/sneakerdropfr.github.io"
GH_FILE    = "releases.json"
GH_API     = f"https://api.github.com/repos/{GH_REPO}/contents/{GH_FILE}"
RAW_URL    = f"https://raw.githubusercontent.com/{GH_REPO}/main/{GH_FILE}"

AWIN_AFFID = "2855487"
AWIN_SNIPES  = "122628"   # Snipes FR
AWIN_SOLEBOX = "20964"    # Solebox

# Domaines cibles
SNIPES_DOMAIN  = "snipes.com/fr-fr"
SOLEBOX_DOMAIN = "solebox.com"

# Paires prioritaires (SKU → délai max en jours avant drop)
PRIORITY_SKUS = {
    "IO1259-400": "AF1 Paisley Hydrogen Blue",
    "IB6843-002": "AF1 Glam Rock Bold Berry",
    "HQ4308-003": "Nike Mind 002 Light Smoke Grey",
}

# IDs à ignorer
SKIP_IDS = {
    "cade-cunningham-x-nike-st-charge-detroit-tough-releases-may-",
    "nike-ja-3-kool-aid-releases-may-2026",
    "nike-kd-19-field-purple-releases-june-2026",
}

# ── LOGGING ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)

# ── HELPERS ─────────────────────────────────────────────────────────────────

def make_awin_url(mid, product_url):
    encoded = urllib.parse.quote(product_url, safe="")
    return f"https://www.awin1.com/cread.php?awinmid={mid}&awinaffid={AWIN_AFFID}&p={encoded}"


def gh_get(url, token):
    """GET GitHub API avec auth."""
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "SneakerDropFR-Bot/1.0"
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def gh_put(url, token, content_b64, sha, message):
    """PUT GitHub API pour mettre à jour un fichier."""
    payload = json.dumps({
        "message": message,
        "content": content_b64,
        "sha": sha
    }).encode()
    req = urllib.request.Request(url, data=payload, method="PUT", headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "SneakerDropFR-Bot/1.0"
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def fetch_url(url, timeout=10):
    """Fetch HTTP simple, retourne (status_code, body_text)."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr-FR,fr;q=0.9"
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def google_search_url(sku, domain):
    """Construit une URL de recherche Google site: pour trouver la page produit."""
    query = urllib.parse.quote(f'site:{domain} "{sku}"')
    return f"https://www.google.com/search?q={query}&hl=fr&num=5"


def extract_product_url(html, domain):
    """Extrait la première URL produit correspondant au domaine depuis les résultats Google."""
    # Pattern : href="/url?q=https://DOMAIN/...&
    pattern = rf'href="/url\?q=(https?://(?:www\.)?{re.escape(domain)}/[^&"]+)'
    matches = re.findall(pattern, html)
    for url in matches:
        url = urllib.parse.unquote(url)
        # Filtrer les pages génériques (homepage, catégories trop courtes)
        if len(url) > len(f"https://{domain}/") + 10:
            # Exclure les pages de résultats de recherche interne
            if "/search" not in url and "?q=" not in url:
                return url
    return None


def verify_url_exists(url):
    """Vérifie qu'une URL retourne 200 ou 301/302 (avec redirect)."""
    status, body = fetch_url(url, timeout=12)
    if status == 200:
        # Vérifier que c'est une vraie page produit (pas une 404 déguisée)
        if "404" in body[:2000] or "not found" in body[:2000].lower():
            return False
        return True
    if status in (301, 302, 303):
        return True
    return False


def search_snipes(sku, title):
    """Cherche une paire sur Snipes FR par SKU. Retourne l'URL produit ou None."""
    log.info(f"  [Snipes] Recherche SKU={sku} titre={title[:40]}")
    
    # 1. Recherche directe sur snipes.com
    search_url = f"https://www.snipes.com/fr-fr/search?q={urllib.parse.quote(sku)}"
    status, body = fetch_url(search_url, timeout=12)
    
    if status == 200 and body:
        # Chercher un lien produit dans la réponse
        patterns = [
            rf'href="(/fr-fr/p/[^"]*{re.escape(sku.lower())}[^"]*)"',
            rf'href="(/fr-fr/p/[^"]+)"',
            rf'"(https://www\.snipes\.com/fr-fr/p/[^"]+)"',
        ]
        for pat in patterns:
            m = re.search(pat, body, re.IGNORECASE)
            if m:
                found = m.group(1)
                if not found.startswith("http"):
                    found = f"https://www.snipes.com{found}"
                log.info(f"  [Snipes] URL trouvée: {found}")
                return found
    
    # 2. Fallback Google
    time.sleep(2)
    g_url = google_search_url(sku, SNIPES_DOMAIN)
    _, g_body = fetch_url(g_url, timeout=12)
    if g_body:
        url = extract_product_url(g_body, SNIPES_DOMAIN)
        if url:
            log.info(f"  [Snipes] URL via Google: {url}")
            return url
    
    log.info(f"  [Snipes] Aucune URL trouvée")
    return None


def search_solebox(sku, title):
    """Cherche une paire sur Solebox par SKU. Retourne l'URL produit ou None."""
    log.info(f"  [Solebox] Recherche SKU={sku} titre={title[:40]}")
    
    # 1. Recherche directe sur solebox.com
    search_url = f"https://www.solebox.com/en_MF/search?q={urllib.parse.quote(sku)}"
    status, body = fetch_url(search_url, timeout=12)
    
    if status == 200 and body:
        patterns = [
            rf'"(https://www\.solebox\.com/[^"]*{re.escape(sku.lower())}[^"]*)"',
            rf'href="(/en_MF/p/[^"]+)"',
        ]
        for pat in patterns:
            m = re.search(pat, body, re.IGNORECASE)
            if m:
                found = m.group(1)
                if not found.startswith("http"):
                    found = f"https://www.solebox.com{found}"
                log.info(f"  [Solebox] URL trouvée: {found}")
                return found
    
    # 2. Fallback Google
    time.sleep(2)
    g_url = google_search_url(sku, SOLEBOX_DOMAIN)
    _, g_body = fetch_url(g_url, timeout=12)
    if g_body:
        url = extract_product_url(g_body, SOLEBOX_DOMAIN)
        if url:
            log.info(f"  [Solebox] URL via Google: {url}")
            return url
    
    log.info(f"  [Solebox] Aucune URL trouvée")
    return None


def already_has_retailer(pair, name):
    """Vérifie si un retailer est déjà présent dans la paire."""
    return any(
        r.get("name", "").lower() == name.lower()
        for r in (pair.get("retailers") or [])
    )


def is_future(date_str):
    """Retourne True si la date est aujourd'hui ou dans le futur."""
    if not date_str or date_str == "TBD":
        return False
    try:
        parts = date_str.split("-")
        drop_date = datetime(int(parts[0]), int(parts[1]), int(parts[2]), tzinfo=timezone.utc)
        now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return drop_date >= now
    except Exception:
        return False


# ── MAIN ────────────────────────────────────────────────────────────────────

def main():
    log.info("═══ Snipes/Solebox Sync START ═══")
    
    # 1. Charger releases.json FRAIS depuis GitHub
    log.info("Chargement releases.json depuis GitHub...")
    try:
        gh_data = gh_get(GH_API, GH_TOKEN)
        sha = gh_data["sha"]
        releases = json.loads(base64.b64decode(gh_data["content"]).decode())
        log.info(f"  {len(releases)} paires chargées (SHA: {sha[:8]})")
    except Exception as e:
        log.error(f"Erreur chargement GitHub: {e}")
        return
    
    today = datetime.now(timezone.utc)
    changes = []
    
    # 2. Filtrer les paires à traiter
    to_process = []
    for pair in releases:
        pid = pair.get("id", "")
        sku = pair.get("sku", "") or ""
        date = pair.get("date", "")
        
        # Ignorer les IDs exclus
        if pid in SKIP_IDS:
            continue
        
        # Ignorer sans SKU
        if not sku:
            continue
        
        # Ignorer les dates passées (plus de 1 jour)
        if not is_future(date):
            continue
        
        # Ignorer si Snipes ET Solebox déjà présents
        has_snipes  = already_has_retailer(pair, "Snipes")
        has_solebox = already_has_retailer(pair, "Solebox")
        if has_snipes and has_solebox:
            continue
        
        to_process.append((pair, sku, has_snipes, has_solebox))
    
    # Trier : paires prioritaires en premier
    def sort_key(item):
        pair, sku, _, __ = item
        return (0 if sku in PRIORITY_SKUS else 1, pair.get("date", "9999"))
    
    to_process.sort(key=sort_key)
    log.info(f"{len(to_process)} paires à vérifier")
    
    # 3. Vérifier chaque paire
    for pair, sku, has_snipes, has_solebox in to_process:
        title = pair.get("title", "")
        pid   = pair.get("id", "")
        log.info(f"\n── {title} ({sku}) ──")
        
        pair_changed = False
        
        # Snipes
        if not has_snipes:
            snipes_url = search_snipes(sku, title)
            if snipes_url:
                # Vérifier que l'URL existe vraiment
                if verify_url_exists(snipes_url):
                    awin_url = make_awin_url(AWIN_SNIPES, snipes_url)
                    if not pair.get("retailers"):
                        pair["retailers"] = []
                    pair["retailers"].append({
                        "name": "Snipes",
                        "url": awin_url,
                        "price": f"{pair.get('price', '')}€" if pair.get("price") else "",
                        "resell": False,
                        "raffle": False
                    })
                    log.info(f"  ✅ Snipes ajouté: {awin_url[:80]}...")
                    changes.append(f"{title} → Snipes")
                    pair_changed = True
                else:
                    log.info(f"  ⚠️ Snipes URL non vérifiée, ignorée")
            time.sleep(3)
        
        # Solebox
        if not has_solebox:
            solebox_url = search_solebox(sku, title)
            if solebox_url:
                if verify_url_exists(solebox_url):
                    awin_url = make_awin_url(AWIN_SOLEBOX, solebox_url)
                    if not pair.get("retailers"):
                        pair["retailers"] = []
                    pair["retailers"].append({
                        "name": "Solebox",
                        "url": awin_url,
                        "price": f"{pair.get('price', '')}€" if pair.get("price") else "",
                        "resell": False,
                        "raffle": False
                    })
                    log.info(f"  ✅ Solebox ajouté: {awin_url[:80]}...")
                    changes.append(f"{title} → Solebox")
                    pair_changed = True
                else:
                    log.info(f"  ⚠️ Solebox URL non vérifiée, ignorée")
            time.sleep(3)
    
    # 4. Push si changements
    if not changes:
        log.info("\nAucun changement — terminé silencieusement")
        return
    
    log.info(f"\n{len(changes)} retailer(s) ajouté(s) — push GitHub...")
    
    content_str = json.dumps(releases, ensure_ascii=False, indent=2)
    content_b64 = base64.b64encode(content_str.encode()).decode()
    
    # GET SHA frais avant PUT
    try:
        fresh = gh_get(GH_API, GH_TOKEN)
        fresh_sha = fresh["sha"]
    except Exception as e:
        log.error(f"Erreur GET SHA frais: {e}")
        return
    
    paires_str = ", ".join(set(c.split(" → ")[0] for c in changes))
    commit_msg = f"feat: retailers Snipes/Solebox — {paires_str}"
    
    try:
        result = gh_put(GH_API, GH_TOKEN, content_b64, fresh_sha, commit_msg)
        commit = result.get("commit", {}).get("sha", "?")[:8]
        log.info(f"✅ Push OK — commit {commit}")
        log.info(f"   Ajouts: {' | '.join(changes)}")
    except Exception as e:
        log.error(f"Erreur push GitHub: {e}")
        return
    
    log.info("═══ Snipes/Solebox Sync END ═══")


if __name__ == "__main__":
    main()
