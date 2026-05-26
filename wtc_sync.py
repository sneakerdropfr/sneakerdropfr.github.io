#!/usr/bin/env python3
"""
wtc_sync.py — Source secondaire/fallback pour les retailers SneakerDropFR
==========================================================================
Rôle : compléter releases.json avec des données WhenToCop UNIQUEMENT
si aucun retailer manuel n'existe déjà pour une release.

Pipeline de priorité (géré par generate_release_pages.py) :
  1. manual_retailers.json  — prioritaire, jamais écrasé
  2. retailers dans releases.json — conservés tels quels
  3. Awin BSTN si domaine actif
  4. buy_url comme lien direct
  5. Fallback "Voir sur WhenToCop"

Ce script ne fait que mettre à jour releases.json pour les releases
sans retailer ET sans entrée dans manual_retailers.json.

NOTE : Le scraping WhenToCop depuis Hetzner est bloqué par Cloudflare.
Ce script est conservé comme fallback pour une future IP résidentielle
ou proxy. En production, utiliser manual_retailers.json.

Usage:
    python3 wtc_sync.py --dry-run        # Voir quelles releases manquent des retailers
    python3 wtc_sync.py --report         # Rapport complet sans modification
    python3 wtc_sync.py --id <id>        # Inspecter une release spécifique

Cron : désactivé par défaut (Cloudflare bloque le VPS Hetzner)
"""

import argparse
import json
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
RELEASES_PATH = os.path.join(ROOT, "releases.json")
MANUAL_RETAILERS_PATH = os.path.join(ROOT, "manual_retailers.json")
LOG_PREFIX = "[wtc_sync]"


def log(msg):
    print(f"{LOG_PREFIX} {datetime.now().strftime('%H:%M:%S')} {msg}", flush=True)


def load_json(path: str) -> dict | list:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_retailer_status(r: dict, manual: dict) -> str:
    """Retourne le statut retailer d'une release."""
    rid = r.get("id", "")
    if rid in manual and manual[rid]:
        return "manual"
    rets = r.get("retailers") or []
    clean = [rt for rt in rets if rt.get("url") and "whentocop" not in rt.get("url", "").lower()]
    if clean:
        return "releases_json"
    buy = r.get("buy_url") or ""
    if buy and "whentocop" not in buy.lower():
        return "buy_url"
    if r.get("wtc_url"):
        return "wtc_fallback"
    return "none"


def report(releases: list, manual: dict) -> dict:
    """Génère un rapport complet sur l'état des retailers."""
    stats = {
        "total": len(releases),
        "manual": 0,
        "releases_json": 0,
        "buy_url": 0,
        "wtc_fallback": 0,
        "none": 0,
        "awin_bstn": 0,
        "corrupted_wtc": 0,
    }
    missing = []
    corrupted = []

    for r in releases:
        rid = r.get("id", "")
        status = get_retailer_status(r, manual)
        stats[status] = stats.get(status, 0) + 1

        if status in ("wtc_fallback", "none"):
            missing.append({"id": rid, "title": r.get("title", "")[:50], "status": status})

        # Vérifier corruption (lien whentocop dans retailers)
        rets = r.get("retailers") or []
        bad = [rt for rt in rets if "whentocop" in rt.get("url", "").lower()]
        if bad:
            corrupted.append(rid)
            stats["corrupted_wtc"] += 1

        # Compter Awin BSTN
        buy = r.get("buy_url") or ""
        if "awinmid=104979" in buy:
            stats["awin_bstn"] += 1

    return {"stats": stats, "missing": missing, "corrupted": corrupted}


def main():
    ap = argparse.ArgumentParser(description="wtc_sync — Retailer pipeline report & fallback")
    ap.add_argument("--id",      help="Inspecter une seule release (partiel)")
    ap.add_argument("--dry-run", action="store_true", help="Afficher sans modifier")
    ap.add_argument("--report",  action="store_true", help="Rapport complet")
    args = ap.parse_args()

    releases = load_json(RELEASES_PATH)
    manual = load_json(MANUAL_RETAILERS_PATH)

    if not isinstance(releases, list):
        log("❌ releases.json invalide")
        return

    log(f"releases.json : {len(releases)} releases")
    log(f"manual_retailers.json : {len(manual)} releases avec retailers manuels")

    # Filtrer si --id
    if args.id:
        targets = [r for r in releases if args.id in r.get("id", "")]
        log(f"\n=== Releases correspondant à '{args.id}' ===")
        for r in targets:
            status = get_retailer_status(r, manual)
            rets = r.get("retailers") or []
            manual_rets = manual.get(r["id"], [])
            log(f"  {r['id']}")
            log(f"    Status     : {status}")
            log(f"    Manual     : {[rt['name'] for rt in manual_rets]}")
            log(f"    Retailers  : {[rt.get('name') for rt in rets[:5]]}")
            log(f"    buy_url    : {r.get('buy_url', '')[:60]}")
            log(f"    wtc_url    : {r.get('wtc_url', '')[:60]}")
        return

    # Rapport
    result = report(releases, manual)
    stats = result["stats"]

    log("\n=== Rapport retailers ===")
    log(f"  Total releases          : {stats['total']}")
    log(f"  ✅ Manual               : {stats['manual']}")
    log(f"  ✅ releases.json        : {stats['releases_json']}")
    log(f"  ✅ buy_url direct       : {stats['buy_url']}")
    log(f"  ⚠️  WTC fallback        : {stats['wtc_fallback']}")
    log(f"  ❌ Aucun lien           : {stats['none']}")
    log(f"  🔗 Awin BSTN actifs     : {stats['awin_bstn']}")
    log(f"  🚨 Corrompus (WTC URL)  : {stats['corrupted_wtc']}")

    if result["corrupted"]:
        log("\n=== Releases corrompues (à nettoyer) ===")
        for rid in result["corrupted"]:
            log(f"  ❌ {rid}")

    if args.report or args.dry_run:
        log(f"\n=== Releases sans retailers ({len(result['missing'])}) ===")
        for m in result["missing"]:
            log(f"  [{m['status']}] {m['id']}")

    log("\n=== Prochaines actions recommandées ===")
    log(f"  → Ajouter manuellement dans manual_retailers.json : {stats['wtc_fallback'] + stats['none']} releases")
    log(f"  → Workflow : screenshot WhenToCop → injection manuelle → regenerate --force")
    log(f"  → Pour activer auto-sync : proxy résidentiel requis (IP Hetzner bloquée Cloudflare)")


if __name__ == "__main__":
    main()
