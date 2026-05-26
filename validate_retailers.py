#!/usr/bin/env python3
"""
validate_retailers.py — Validation complète du pipeline retailers SneakerDropFR
================================================================================
Vérifie :
  1. Aucun lien whentocop dans releases.json comme retailer
  2. Nombre de releases avec retailers valides
  3. Nombre de liens BSTN affiliés Awin
  4. Nombre de liens directs par source
  5. Pages sorties/ sans liens whentocop hors fallback officiel

Usage:
    python3 validate_retailers.py             # Validation complète
    python3 validate_retailers.py --fix       # Nettoie les retailers corrompus
    python3 validate_retailers.py --pages     # Vérifie aussi les fichiers HTML
"""

import argparse
import json
import os
import re
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
RELEASES_PATH    = os.path.join(ROOT, "releases.json")
MANUAL_PATH      = os.path.join(ROOT, "manual_retailers.json")
AFFILIATE_PATH   = os.path.join(ROOT, "affiliate_mapping.json")
SORTIES_DIR      = os.path.join(ROOT, "sorties")

OK   = "✅"
WARN = "⚠️ "
FAIL = "❌"


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def check_releases(releases: list, manual: dict) -> dict:
    """Validation de releases.json."""
    results = {
        "total": len(releases),
        "no_id": 0,
        "duplicates": [],
        "corrupted_wtc": [],
        "with_retailers": 0,
        "with_manual": 0,
        "with_releases_json": 0,
        "with_buy_url": 0,
        "wtc_fallback": 0,
        "no_link": 0,
        "awin_bstn": 0,
        "awin_sneakers": 0,
        "direct_links": 0,
    }

    seen_ids = {}
    for r in releases:
        rid = r.get("id", "")
        if not rid:
            results["no_id"] += 1
            continue

        # Doublons
        if rid in seen_ids:
            results["duplicates"].append(rid)
        seen_ids[rid] = True

        # Retailers corrompus (URL whentocop)
        rets = r.get("retailers") or []
        bad = [rt for rt in rets if "whentocop" in rt.get("url", "").lower()]
        if bad:
            results["corrupted_wtc"].append(rid)

        # Source retailers
        has_manual = rid in manual and bool(manual[rid])
        has_releases = bool([rt for rt in rets if rt.get("url") and "whentocop" not in rt.get("url", "").lower()])
        buy = r.get("buy_url") or ""
        has_buy = bool(buy and "whentocop" not in buy.lower())
        has_wtc = bool(r.get("wtc_url"))

        if has_manual:
            results["with_manual"] += 1
            results["with_retailers"] += 1
        elif has_releases:
            results["with_releases_json"] += 1
            results["with_retailers"] += 1
        elif has_buy:
            results["with_buy_url"] += 1
            results["with_retailers"] += 1
        elif has_wtc:
            results["wtc_fallback"] += 1
        else:
            results["no_link"] += 1

        # Awin
        if "awinmid=104979" in buy:
            results["awin_bstn"] += 1
        if "awinmid=16329" in buy:
            results["awin_sneakers"] += 1

        # Liens directs (retail, pas resell, pas whentocop)
        for rt in rets:
            u = rt.get("url", "")
            if u and "whentocop" not in u.lower() and not rt.get("resell"):
                results["direct_links"] += 1

    return results


def check_pages(releases: list, manual: dict) -> dict:
    """Vérifie les fichiers HTML dans sorties/."""
    results = {
        "checked": 0,
        "ok": 0,
        "wtc_as_retailer": [],   # lien WTC comme vrai retailer (pas fallback)
        "missing_canonical": [],
        "missing_jsonld": [],
        "title_too_long": [],
    }

    for r in releases:
        rid = r.get("id", "")
        fpath = os.path.join(SORTIES_DIR, f"{rid}.html")
        if not os.path.exists(fpath):
            continue
        results["checked"] += 1

        with open(fpath, encoding="utf-8") as f:
            html = f.read()

        # Vérifier canonical
        if not re.search(r'<link rel="canonical"', html):
            results["missing_canonical"].append(rid)

        # Vérifier JSON-LD
        if "ld+json" not in html:
            results["missing_jsonld"].append(rid)

        # Titre trop long
        tm = re.search(r'<title>(.+?)</title>', html)
        if tm and len(tm.group(1)) > 60:
            results["title_too_long"].append(f"{rid} ({len(tm.group(1))}c)")

        # Retailer nommé whentocop (hors fallback "Voir sur WhenToCop")
        names = re.findall(r'<span class="retailer__name">(.+?)</span>', html)
        bad_names = [n for n in names if "whentocop" in n.lower() and n != "Voir sur WhenToCop"]
        if bad_names:
            results["wtc_as_retailer"].append({"id": rid, "names": bad_names})

        if not results["missing_canonical"] or rid not in results["missing_canonical"]:
            if not results["missing_jsonld"] or rid not in results["missing_jsonld"]:
                if not any(d["id"] == rid for d in results["wtc_as_retailer"]):
                    results["ok"] += 1

    return results


def fix_corrupted(releases: list) -> int:
    """Nettoie les retailers avec URL whentocop dans releases.json."""
    fixed = 0
    for r in releases:
        rets = r.get("retailers") or []
        clean = [rt for rt in rets if "whentocop" not in rt.get("url", "").lower()]
        if len(clean) < len(rets):
            r["retailers"] = clean
            r.pop("_wtc_synced", None)
            fixed += 1
    return fixed


def print_section(title: str):
    print(f"\n{'─'*50}")
    print(f" {title}")
    print(f"{'─'*50}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix",   action="store_true", help="Nettoyer les retailers corrompus")
    ap.add_argument("--pages", action="store_true", help="Vérifier aussi les fichiers HTML")
    args = ap.parse_args()

    print(f"\n{'='*50}")
    print(f" validate_retailers.py — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*50}")

    # Charger les fichiers
    releases = load(RELEASES_PATH)
    manual   = load(MANUAL_PATH) or {}
    affiliate = load(AFFILIATE_PATH) or {}

    if not releases:
        print(f"{FAIL} releases.json introuvable ou invalide")
        return

    # ── 1. Vérification releases.json ──
    print_section("1. releases.json")
    r = check_releases(releases, manual)

    print(f"  Total releases           : {r['total']}")
    print(f"  {OK if r['no_id']==0 else FAIL} Sans ID                : {r['no_id']}")
    print(f"  {OK if not r['duplicates'] else FAIL} IDs dupliqués          : {len(r['duplicates'])} {r['duplicates'] or ''}")
    print(f"  {OK if not r['corrupted_wtc'] else FAIL} Retailers corrompus    : {len(r['corrupted_wtc'])}")
    if r['corrupted_wtc']:
        for rid in r['corrupted_wtc']:
            print(f"      {FAIL} {rid}")

    # ── 2. Sources retailers ──
    print_section("2. Sources retailers")
    print(f"  {OK} Manual                  : {r['with_manual']}/{r['total']}")
    print(f"  {OK} releases.json           : {r['with_releases_json']}/{r['total']}")
    print(f"  {OK} buy_url direct          : {r['with_buy_url']}/{r['total']}")
    print(f"  {WARN} WTC fallback           : {r['wtc_fallback']}/{r['total']}")
    print(f"  {FAIL if r['no_link']>0 else OK} Aucun lien            : {r['no_link']}/{r['total']}")
    total_with = r['with_manual'] + r['with_releases_json'] + r['with_buy_url']
    coverage = round(total_with / r['total'] * 100) if r['total'] else 0
    print(f"\n  Couverture retailers     : {total_with}/{r['total']} ({coverage}%)")

    # ── 3. Affiliation Awin ──
    print_section("3. Affiliation Awin")
    print(f"  {OK} BSTN (awinmid=104979)  : {r['awin_bstn']} liens")
    print(f"  {OK} Sneakers.fr (16329)    : {r['awin_sneakers']} liens")
    print(f"  {OK} Liens directs retail   : {r['direct_links']}")

    # Vérifier pending
    for domain, cfg in affiliate.items():
        if domain.startswith("_"): continue
        status = cfg.get("status", "")
        mid = cfg.get("awinmid", "")
        icon = OK if status == "active" else WARN if status == "pending" else "—"
        print(f"  {icon} {cfg.get('retailer', domain):<20} status={status} mid={mid or 'TBD'}")

    # ── 4. Vérification pages HTML ──
    if args.pages:
        print_section("4. Pages sorties/")
        p = check_pages(releases, manual)
        print(f"  Pages vérifiées          : {p['checked']}")
        print(f"  {OK} Pages OK               : {p['ok']}")
        print(f"  {OK if not p['wtc_as_retailer'] else FAIL} WTC comme retailer     : {len(p['wtc_as_retailer'])}")
        print(f"  {OK if not p['missing_canonical'] else FAIL} Sans canonical         : {len(p['missing_canonical'])}")
        print(f"  {OK if not p['missing_jsonld'] else FAIL} Sans JSON-LD           : {len(p['missing_jsonld'])}")
        print(f"  {OK if not p['title_too_long'] else WARN} Titres trop longs      : {len(p['title_too_long'])}")
        if p['wtc_as_retailer']:
            for item in p['wtc_as_retailer']:
                print(f"    {FAIL} {item['id']}: {item['names']}")

    # ── 5. Fix ──
    if args.fix and r['corrupted_wtc']:
        print_section("5. Fix retailers corrompus")
        fixed = fix_corrupted(releases)
        with open(RELEASES_PATH, "w", encoding="utf-8") as f:
            json.dump(releases, f, ensure_ascii=False, indent=2)
        print(f"  {OK} {fixed} releases nettoyées — releases.json sauvegardé")
        print(f"  → Relancer : python3 generate_release_pages.py --force")

    # ── Résumé ──
    print_section("Résumé")
    all_ok = (
        r['no_id'] == 0 and
        not r['duplicates'] and
        not r['corrupted_wtc']
    )
    print(f"  {'✅ VALID' if all_ok else '❌ PROBLÈMES DÉTECTÉS'}")
    if r['wtc_fallback'] > 0:
        print(f"  → {r['wtc_fallback']} releases en attente de retailers manuels")
        print(f"     Workflow : screenshot WhenToCop → manual_retailers.json → regenerate --force")


if __name__ == "__main__":
    main()
