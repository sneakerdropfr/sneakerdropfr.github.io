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
    api_responses = []
    back_responses = []

    # ── Intercepter TOUTES les réponses JSON + back.whentocop.fr ──
    async def on_response(response):
        url = response.url
        ct = response.headers.get("content-type", "")
        if "application/json" in ct or url.endswith(".json"):
            try:
                body = await response.json()
                api_responses.append({"url": url, "body": body})
                # Capturer spécifiquement back.whentocop.fr
                if "back.whentocop" in url or ("whentocop" in url and "drops" in url and url != wtc_url):
                    back_responses.append({"url": url, "body": body})
                    log(f"  🎯 back.whentocop: {url[:80]} keys={list(body.keys())[:8] if isinstance(body,dict) else 'list:'+str(len(body))}")
            except Exception:
                pass

    page.on("response", on_response)

    try:
        await page.goto(wtc_url, wait_until="domcontentloaded", timeout=25000)

        # Attendre que la section retailers apparaisse dans le DOM
        try:
            await page.wait_for_function(
                "() => document.querySelectorAll('a[href]').length > 20",
                timeout=10000
            )
        except Exception:
            pass

        # Scroller progressivement pour déclencher le lazy loading
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
        await asyncio.sleep(1.5)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await asyncio.sleep(1.5)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(3)

    except Exception as e:
        log(f"  ⚠️  Timeout/erreur chargement: {e}")
        page.remove_listener("response", on_response)
        return result

    page.remove_listener("response", on_response)

    log(f"  🔍 Réponses JSON: {len(api_responses)} | back.whentocop: {len(back_responses)}")
    for api in api_responses:
        log(f"     {api['url'][:90]}")

    # ── Traiter d'abord les réponses back.whentocop (retailers directs) ──
    RESELL_D = ["stockx.com", "goat.com", "klekt.com"]
    RETAIL_D = [
        "footpatrol.com","snipes.com","offspring.co.uk","footshop.eu",
        "sevenstore.com","size.co.uk","urbanstar","nike.com",
        "adidas.fr","adidas.com","jdsports","footlocker",
        "courir.com","bstn.com","zalando","goat.com","stockx.com",
        "klekt.com","sns","solebox","sneakers.fr","end-clothing",
    ]

    for api in back_responses:
        body = api["body"]
        items = body if isinstance(body, list) else body.get("retailers") or body.get("items") or body.get("data") or []
        if not isinstance(items, list):
            continue
        for rt in items:
            if not isinstance(rt, dict): continue
            u = rt.get("url") or rt.get("link") or rt.get("href") or rt.get("redirectUrl") or rt.get("buyUrl") or ""
            if not u or "whentocop" in u.lower(): continue
            if not any(d in u for d in RETAIL_D): continue
            name = rt.get("name") or rt.get("retailer") or rt.get("shopName") or u.split("/")[2]
            price = rt.get("price") or rt.get("retailPrice")
            entry = {"name": str(name)[:40], "url": u}
            if price: entry["price"] = str(price)
            if any(d in u for d in RESELL_D): entry["resell"] = True
            result["retailers"].append(entry)

    if result["retailers"]:
        log(f"  ✅ {len(result['retailers'])} retailers via back.whentocop")
        return result

    # ── Analyser les réponses API capturées ──
    RESELL_DOMAINS = ["stockx.com", "goat.com", "klekt.com"]
    RETAILER_DOMAINS = [
        "footpatrol.com", "snipes.com", "offspring.co.uk", "footshop.eu",
        "sevenstore.com", "size.co.uk", "urbanstar", "nike.com",
        "adidas.fr", "adidas.com", "jdsports", "footlocker",
        "courir.com", "bstn.com", "zalando", "goat.com", "stockx.com",
        "klekt.com", "sns", "solebox", "sneakers.fr", "end-clothing",
    ]

    for api in api_responses:
        body = api["body"]
        retailers_raw = []
        # Chercher une clé retailers/shops/partners dans la réponse
        if isinstance(body, dict):
            for key in ["retailers", "shops", "partners", "links", "where_to_buy", "offers"]:
                if key in body and isinstance(body[key], list):
                    retailers_raw = body[key]
                    break
            # Parfois dans data.retailers
            if not retailers_raw and "data" in body and isinstance(body["data"], dict):
                for key in ["retailers", "shops", "partners", "links"]:
                    if key in body["data"] and isinstance(body["data"][key], list):
                        retailers_raw = body["data"][key]
                        break
        elif isinstance(body, list):
            retailers_raw = body

        for rt in retailers_raw:
            if not isinstance(rt, dict):
                continue
            url = rt.get("url") or rt.get("link") or rt.get("href") or ""
            if not url or "whentocop" in url.lower():
                continue
            if not any(d in url for d in RETAILER_DOMAINS):
                continue
            name = rt.get("name") or rt.get("retailer") or rt.get("shop") or url.split("/")[2]
            price = rt.get("price") or rt.get("retail_price")
            is_resell = any(d in url for d in RESELL_DOMAINS)
            entry = {"name": str(name)[:40], "url": url}
            if price:
                entry["price"] = str(price)
            if is_resell:
                entry["resell"] = True
            result["retailers"].append(entry)

    if result["retailers"]:
        log(f"  ✅ {len(result['retailers'])} retailers via API intercept")
        return result

    html = await page.content()

    # ── Retailers via __NEXT_DATA__ (Next.js) ──
    try:
        next_data_str = await page.evaluate("() => window.__NEXT_DATA__ ? JSON.stringify(window.__NEXT_DATA__) : null")
        if next_data_str:
            nd = json.loads(next_data_str)
            pp = nd.get("props", {}).get("pageProps", {})
            build_id = nd.get("buildId", "")
            slug_path = nd.get("page", "").replace("/[locale]", "/fr")
            product_id = pp.get("productId", "")
            slug = pp.get("slug", "")
            log(f"  🔍 buildId={build_id} slug={slug} productId={product_id}")

            RESELL_D = ["stockx.com", "goat.com", "klekt.com"]
            RETAIL_D = [
                "footpatrol.com","snipes.com","offspring.co.uk","footshop.eu",
                "sevenstore.com","size.co.uk","urbanstar","nike.com",
                "adidas.fr","adidas.com","jdsports","footlocker",
                "courir.com","bstn.com","zalando","goat.com","stockx.com",
                "klekt.com","sns","solebox","sneakers.fr","end-clothing",
                "size?","offspring","footshop","snipes",
            ]

            # ── Essayer de récupérer les retailers via API directe ──
            api_candidates = []
            if build_id and slug:
                api_candidates.append(
                    f"https://www.whentocop.fr/_next/data/{build_id}/fr/drops/{slug}.json"
                )
            if product_id:
                api_candidates += [
                    f"https://back.whentocop.fr/v1/drops/{product_id}/retailers",
                    f"https://back.whentocop.fr/drops/{product_id}/retailers",
                    f"https://back.whentocop.fr/v1/products/{product_id}/retailers",
                ]

            for api_url in api_candidates:
                try:
                    log(f"  🔍 Tentative API: {api_url}")
                    resp = await page.goto(api_url, wait_until="domcontentloaded", timeout=10000)
                    if resp and resp.status == 200:
                        try:
                            api_data = await resp.json()
                        except Exception:
                            text = await page.inner_text("body")
                            api_data = json.loads(text)

                        log(f"  🔍 API OK — type={type(api_data).__name__} keys={list(api_data.keys())[:10] if isinstance(api_data, dict) else 'list:'+str(len(api_data))}")

                        # Parser selon structure
                        items = []
                        if isinstance(api_data, list):
                            items = api_data
                        elif isinstance(api_data, dict):
                            pp2 = api_data.get("pageProps", api_data)
                            log(f"  🔍 pageProps2 keys: {list(pp2.keys())[:15]}")
                            # Explorer récursivement les sous-objets
                            for k, v in pp2.items():
                                if isinstance(v, dict):
                                    log(f"  🔍 pp2[{k}] keys: {list(v.keys())[:10]}")
                                elif isinstance(v, list) and v:
                                    log(f"  🔍 pp2[{k}] list[{len(v)}] ex: {list(v[0].keys())[:8] if isinstance(v[0], dict) else str(v[0])[:60]}")
                            drop2 = pp2.get("drop") or pp2.get("product") or pp2.get("release") or pp2.get("item") or {}
                            for key in ["retailers","shops","partners","links","where_to_buy","offers","stores","items","buyLinks","whereToGet"]:
                                raw = (drop2 or pp2).get(key)
                                if raw and isinstance(raw, list):
                                    items = raw
                                    log(f"  🔍 Clé '{key}': {len(items)} entrées | ex: {list(items[0].keys())[:8] if isinstance(items[0],dict) else items[0]}")
                                    break

                        for rt in items:
                            if not isinstance(rt, dict): continue
                            u = rt.get("url") or rt.get("link") or rt.get("href") or rt.get("redirectUrl") or rt.get("buyUrl") or ""
                            if not u or "whentocop" in u.lower(): continue
                            if not any(d in u for d in RETAIL_D): continue
                            name = rt.get("name") or rt.get("retailer") or rt.get("shopName") or rt.get("shop") or u.split("/")[2]
                            price = rt.get("price") or rt.get("retail_price") or rt.get("retailPrice")
                            entry = {"name": str(name)[:40], "url": u}
                            if price: entry["price"] = str(price)
                            if any(d in u for d in RESELL_D): entry["resell"] = True
                            result["retailers"].append(entry)

                        if result["retailers"]:
                            log(f"  ✅ {len(result['retailers'])} retailers via API {api_url}")
                            # Revenir sur la page originale
                            await page.goto(wtc_url, wait_until="domcontentloaded", timeout=15000)
                            break
                except Exception as e:
                    log(f"  ⚠️  API {api_url} erreur: {e}")
                    continue

            # Extraire prix et date depuis Query[1]
            dehydrated = pp.get("dehydratedState", {})
            queries = dehydrated.get("queries", [])
            for q in queries:
                qdata = q.get("state", {}).get("data", {})
                if not isinstance(qdata, dict): continue
                body = qdata.get("body") or qdata
                if not isinstance(body, dict): continue
                if "retailPrice" in body and not result.get("price"):
                    p = body.get("retailPrice")
                    if p: result["price"] = f"{p}€"
                if "dropDate" in body and not result.get("date"):
                    result["_dropDate"] = body.get("dropDate")

    except Exception as e:
        log(f"  ⚠️  __NEXT_DATA__ erreur: {e}")

    except Exception as e:
        log(f"  ⚠️  __NEXT_DATA__ erreur: {e}")

    if result["retailers"]:
        log(f"  ✅ {len(result['retailers'])} retailers via __NEXT_DATA__")
        return result

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
                    // Exclure liens internes WhenToCop
                    if (href.includes('whentocop.fr') || href.includes('whentocop.com') || href.includes('whentocop.')) return;
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

    # ── Fallback : attendre JS puis re-extraire ──
    if not result["retailers"]:
        log("  ↩️  Fallback JS wait + re-extract...")
        # Attendre que les liens retailers apparaissent dans le DOM
        WAIT_SELECTORS = (
            'a[href*="footpatrol"], a[href*="snipes"], a[href*="size.co"],'
            'a[href*="offspring"], a[href*="footshop"], a[href*="sevenstore"],'
            'a[href*="nike.com/launch"], a[href*="stockx"], a[href*="goat.com"],'
            'a[href*="jdsports"], a[href*="footlocker"], a[href*="bstn"]'
        )
        try:
            await page.wait_for_selector(WAIT_SELECTORS, timeout=8000)
        except Exception:
            pass
        await asyncio.sleep(2)

        js_code = """
        () => {
            const RETAILER_DOMAINS = [
                'footpatrol.com','snipes.com','offspring.co.uk','footshop.eu',
                'sevenstore.com','size.co.uk','urbanstar','nike.com',
                'adidas.fr','adidas.com','jdsports','footlocker',
                'courir.com','bstn.com','zalando','goat.com','stockx.com',
                'klekt.com','sns','solebox','sivasdescalzo','sneakers.fr',
                'end-clothing','flatspot'
            ];
            const RESELL_DOMAINS = ['stockx.com','goat.com','klekt.com'];
            const results = [];
            const seen = new Set();
            document.querySelectorAll('a[href]').forEach(a => {
                const href = a.href;
                if (!href || href.includes('whentocop')) return;
                if (seen.has(href)) return;
                if (!RETAILER_DOMAINS.some(d => href.includes(d))) return;
                seen.add(href);
                const text = a.innerText.trim();
                const name = text.split('\\n')[0].slice(0, 40) || href.split('/')[2] || 'Retailer';
                const priceM = text.match(/(\\d+)\\s*€/);
                results.push({
                    name: name,
                    url: href,
                    price: priceM ? priceM[1] + '€' : null,
                    resell: RESELL_DOMAINS.some(d => href.includes(d)),
                });
            });
            return results;
        }
        """
        try:
            links_data = await page.evaluate(js_code)
            if links_data:
                seen_urls = set()
                for rt in links_data:
                    u = rt.get("url", "")
                    if u and u not in seen_urls:
                        seen_urls.add(u)
                        entry = {"name": rt["name"], "url": u}
                        if rt.get("price"):
                            entry["price"] = rt["price"]
                        if rt.get("resell"):
                            entry["resell"] = True
                        result["retailers"].append(entry)
            if result["retailers"]:
                log(f"  ✅ {len(result['retailers'])} retailers via fallback JS")
        except Exception as e:
            log(f"  ⚠️  Fallback JS erreur: {e}")

    # ── Raffle globale ──
    raffle_keywords = ["raffle", "tirage au sort", "inscriptions", "draw"]
    if any(kw in html.lower() for kw in raffle_keywords):
        result["raffle"] = True

    # ── Fallback DOM final — debug total liens ──
    if not result["retailers"]:
        try:
            total_links = await page.evaluate("() => document.querySelectorAll('a[href]').length")
            ext_links = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]'))
                .map(a => a.href)
                .filter(h => h && !h.includes('whentocop') && h.startsWith('http'))
                .slice(0, 20)
            """)
            log(f"  🔍 Total liens: {total_links} | Externes (20 max): {ext_links}")
        except Exception as e:
            log(f"  ⚠️  Debug liens: {e}")

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

    # ── Cookies WhenToCop (chargés depuis .env ou wtc_cookies.json) ──
    wtc_cookies = []
    cookies_path = os.path.join(ROOT, "wtc_cookies.json")
    if os.path.exists(cookies_path):
        try:
            with open(cookies_path, encoding="utf-8") as f:
                raw_cookies = json.load(f)
            # Convertir au format Playwright
            for c in raw_cookies:
                domain = c.get("domain", "")
                # Nettoyer le domaine si format markdown
                if "](http" in domain:
                    domain = domain.split("](")[0].lstrip("[")
                entry = {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": domain,
                    "path": c.get("path", "/"),
                    "secure": c.get("secure", False),
                    "httpOnly": c.get("httpOnly", False),
                }
                if c.get("expirationDate"):
                    entry["expires"] = int(c["expirationDate"])
                wtc_cookies.append(entry)
            log(f"✅ {len(wtc_cookies)} cookies WhenToCop chargés")
        except Exception as e:
            log(f"⚠️  Erreur chargement cookies: {e}")
    else:
        log("⚠️  wtc_cookies.json absent — Cloudflare risque de bloquer")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="fr-FR",
            viewport={"width": 1280, "height": 800},
        )
        # Injecter les cookies avant toute navigation
        if wtc_cookies:
            await context.add_cookies(wtc_cookies)
            log("✅ Cookies injectés dans le contexte Playwright")
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
