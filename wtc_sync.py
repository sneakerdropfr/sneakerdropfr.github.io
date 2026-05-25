#!/usr/bin/env python3
"""
wtc_sync.py — Synchronisation automatique WhenToCop -> releases.json
======================================================================
Ce script lit releases.json, visite chaque page WhenToCop via Playwright,
extrait les retailers (nom, url, prix, raffle, resell), et met à jour
releases.json + régénère les pages HTML.

Usage:
    python3 wtc_sync.py                    # Toutes les releases avec wtc_url
    python3 wtc_sync.py --id air-jordan-3  # Une seule release
    python3 wtc_sync.py --dry-run          # Aperçu sans écriture
    python3 wtc_sync.py --force            # Même les releases déjà renseignées

Cron suggéré (quotidien 5h00) :
    0 5 * * * cd /root/sneakerdropfr.github.io && python3 wtc_sync.py >> /var/log/wtc_sync.log 2>&1
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from html import escape

ROOT = os.path.dirname(os.path.abspath(__file__))
RELEASES_PATH = os.path.join(ROOT, "releases.json")
LOG_PREFIX = "[wtc_sync]"


def log(msg):
    print(f"{LOG_PREFIX} {datetime.now().strftime('%H:%M:%S')} {msg}", flush=True)


# ── Extraction WhenToCop ──────────────────────────────────────────────────────

async def fetch_wtc_retailers(page, wtc_url: str) -> dict:
    """
    Visite une page WhenToCop et extrait :
    - date, prix, sku
    - retailers (nom, url, prix, type: retail/raffle/resell)
    Retourne un dict avec les champs à merger dans releases.json.
    """
    result = {"retailers": [], "_wtc_synced": True}

    try:
        await page.goto(wtc_url, wait_until="networkidle", timeout=25000)
        await asyncio.sleep(1.5)
    except Exception as e:
        log(f"  ⚠️  Timeout/erreur chargement: {e}")
        return result

    html = await page.content()

    # ── Date ──
    date_match = re.search(
        r'(?:Date de sortie|Release date)[^<]*?[:]\s*<[^>]*>\s*(\d{1,2})\s+(\w+)\s+(\d{4})',
        html, re.IGNORECASE
    )
    if not date_match:
        # Chercher le badge date en haut de page
        date_match = re.search(
            r'<span[^>]*>\s*(\d{1,2})\s*</span>\s*<span[^>]*>\s*(\w+)\s*</span>',
            html
        )

    # ── Prix ──
    price_match = re.search(
        r'Prix\s*[:\s]*<[^>]*>\s*(\d+)\s*€', html, re.IGNORECASE
    )
    if price_match:
        result["price"] = f"{price_match.group(1)}€"

    # ── SKU ──
    sku_match = re.search(
        r'(?:Code SKU|SKU)\s*[:\s]*<[^>]*>\s*([A-Z0-9]{5,12}-\d{3})',
        html, re.IGNORECASE
    )
    if sku_match:
        result["sku"] = sku_match.group(1)

    # ── Retailers via JS DOM ──
    try:
        retailers_data = await page.evaluate("""
        () => {
            const results = [];

            // Sélecteurs possibles pour les cartes retailer
            const selectors = [
                '[class*="retailer"]',
                '[class*="partner"]',
                '[class*="shop-card"]',
                '[class*="where-to-buy"]',
                'a[href*="footpatrol"]',
                'a[href*="snipes"]',
                'a[href*="offspring"]',
                'a[href*="footshop"]',
                'a[href*="sevenstore"]',
                'a[href*="size.co"]',
                'a[href*="urbanstar"]',
                'a[href*="nike.com"]',
                'a[href*="adidas"]',
                'a[href*="jdsports"]',
                'a[href*="footlocker"]',
                'a[href*="courir"]',
                'a[href*="bstn"]',
                'a[href*="snkrs"]',
                'a[href*="zalando"]',
                'a[href*="goat.com"]',
                'a[href*="stockx"]',
                'a[href*="klekt"]',
            ];

            const seen = new Set();

            for (const sel of selectors) {
                document.querySelectorAll(sel).forEach(el => {
                    const href = el.href || el.querySelector('a')?.href || '';
                    if (!href || href === window.location.href) return;
                    if (seen.has(href)) return;
                    seen.add(href);

                    const text = el.innerText || '';
                    const name = el.querySelector('[class*="name"], h3, h4, strong, b')?.innerText
                                || el.getAttribute('aria-label')
                                || text.split('\\n')[0].trim();

                    // Détecter prix
                    const priceMatch = text.match(/(\\d+)\\s*€/);
                    const price = priceMatch ? priceMatch[1] + '€' : null;

                    // Détecter type
                    const lowerText = text.toLowerCase();
                    const lowerHref = href.toLowerCase();
                    const isResell = lowerHref.includes('stockx') || lowerHref.includes('goat.com')
                                   || lowerHref.includes('klekt') || lowerText.includes('resell');
                    const isRaffle = lowerText.includes('raffle') || lowerText.includes('tirage')
                                   || lowerText.includes('inscription') || lowerText.includes('draw');

                    results.push({
                        name: name?.trim().slice(0, 40) || 'Retailer',
                        url: href,
                        price: price,
                        resell: isResell,
                        raffle: isRaffle || false,
                    });
                });
            }

            return results;
        }
        """)
        if retailers_data:
            # Dédupliquer par URL
            seen_urls = set()
            clean = []
            for r in retailers_data:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    entry = {
                        "name": r["name"],
                        "url": url,
                    }
                    if r.get("price"):
                        entry["price"] = r["price"]
                    if r.get("resell"):
                        entry["resell"] = True
                    if r.get("raffle"):
                        entry["raffle"] = True
                    clean.append(entry)

            result["retailers"] = clean
            log(f"  ✅ {len(clean)} retailers extraits via DOM")

    except Exception as e:
        log(f"  ⚠️  Erreur extraction DOM: {e}")

    # ── Fallback : parser le HTML brut ──
    if not result["retailers"]:
        log("  ↩️  Fallback parsing HTML...")
        # Chercher les liens vers des domaines retailers connus
        known_domains = [
            "footpatrol", "snipes", "offspring", "footshop", "sevenstore",
            "size.co.uk", "urbanstar", "nike.com", "adidas", "jdsports",
            "footlocker", "courir", "bstn", "zalando", "goat.com", "stockx",
            "klekt", "sns", "solebox", "sivasdescalzo",
        ]
        links = re.findall(r'href=["\']([^"\']+)["\']', html)
        seen = set()
        for link in links:
            if any(d in link for d in known_domains) and link not in seen:
                seen.add(link)
                domain = re.sub(r'https?://(www\.)?', '', link).split('/')[0]
                is_resell = any(d in link for d in ["stockx", "goat.com", "klekt"])
                result["retailers"].append({
                    "name": domain,
                    "url": link,
                    "resell": is_resell,
                })

        if result["retailers"]:
            log(f"  ✅ {len(result['retailers'])} retailers via fallback HTML")

    # ── Raffle globale ──
    raffle_keywords = ["raffle", "tirage au sort", "inscriptions", "draw"]
    if any(kw in html.lower() for kw in raffle_keywords):
        result["raffle"] = True

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

async def run(args):
    from playwright.async_api import async_playwright

    with open(RELEASES_PATH, encoding="utf-8") as f:
        releases = json.load(f)

    # Filtrer les releases à traiter
    to_process = []
    for r in releases:
        wtc_url = r.get("wtc_url", "")
        if not wtc_url or "whentocop" not in wtc_url:
            continue
        if args.id and args.id not in r.get("id", ""):
            continue
        # Sauter si déjà renseigné (sauf --force)
        if not args.force:
            existing_rets = r.get("retailers") or []
            retail_count = sum(1 for rt in existing_rets if not rt.get("resell"))
            if retail_count >= 2 and r.get("_wtc_synced"):
                continue
        to_process.append(r)

    log(f"Releases à synchroniser: {len(to_process)}")
    if args.dry_run:
        for r in to_process:
            log(f"  DRY-RUN: {r['id']}")
        return

    updated = 0
    errors = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
            locale="fr-FR",
        )
        page = await context.new_page()

        for i, r in enumerate(to_process):
            log(f"[{i+1}/{len(to_process)}] {r['id']}")
            try:
                data = await fetch_wtc_retailers(page, r["wtc_url"])

                if data.get("retailers"):
                    r["retailers"] = data["retailers"]
                    updated += 1
                if data.get("price") and not r.get("price"):
                    r["price"] = data["price"]
                if data.get("sku") and not r.get("sku"):
                    r["sku"] = data["sku"]
                if data.get("raffle"):
                    r["raffle"] = True
                r["_wtc_synced"] = True

            except Exception as e:
                log(f"  ❌ Erreur: {e}")
                errors += 1

            # Pause entre les pages pour éviter le rate-limit
            await asyncio.sleep(2)

        await browser.close()

    # Sauvegarder releases.json
    with open(RELEASES_PATH, "w", encoding="utf-8") as f:
        json.dump(releases, f, ensure_ascii=False, indent=2)

    log(f"✅ releases.json mis à jour: {updated} releases")
    log(f"❌ Erreurs: {errors}")

    # Régénérer les pages HTML
    if updated > 0:
        log("Régénération des pages HTML...")
        import subprocess
        result = subprocess.run(
            ["python3", "generate_release_pages.py", "--force", "--update-sitemap"],
            cwd=ROOT, capture_output=True, text=True
        )
        log(result.stdout.strip())

        # Push sur GitHub
        log("Push sur GitHub...")
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            subprocess.run(
                ["git", "add", "releases.json", "sorties/", "sitemap.xml"],
                cwd=ROOT
            )
            subprocess.run(
                ["git", "commit", "-m", "auto: sync retailers from WhenToCop"],
                cwd=ROOT
            )
            subprocess.run(
                ["git", "push", f"https://{token}@github.com/sneakerdropfr/sneakerdropfr.github.io.git", "main"],
                cwd=ROOT
            )
            log("✅ Pushed to GitHub")
        else:
            log("⚠️  GITHUB_TOKEN non défini — push manuel requis")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id",      help="Traiter une seule release (partiel)")
    ap.add_argument("--force",   action="store_true", help="Traiter même les releases déjà synchées")
    ap.add_argument("--dry-run", action="store_true", help="Afficher sans modifier")
    args = ap.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
