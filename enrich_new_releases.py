#!/usr/bin/env python3
"""
enrich_new_releases.py — Enrichissement automatique des nouvelles releases
==========================================================================
Détecte les entrées dans releases.json (et releases_past.json) qui manquent
de colorway, silhouette ou year, et les renseigne automatiquement via :
  1. Extraction heuristique depuis le titre / l'id
  2. Fallback : recherche web via Perplexity (si --web flag)

Usage :
    python3 enrich_new_releases.py              # dry-run : affiche ce qui manque
    python3 enrich_new_releases.py --apply      # applique les enrichissements
    python3 enrich_new_releases.py --apply --web  # avec fallback web
    python3 enrich_new_releases.py --apply --file releases_past.json

Cron recommandé (VPS, après chaque git pull) :
    python3 /var/www/sneakerdropfr/enrich_new_releases.py --apply
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_PREFIX = "[enrich]"


def log(msg):
    print(f"{LOG_PREFIX} {datetime.now().strftime('%H:%M:%S')} {msg}", flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# PATTERNS SILHOUETTE
# ─────────────────────────────────────────────────────────────────────────────

SILHOUETTE_PATTERNS = [
    # Jordan
    (r'\bair\s+jordan\s+1\s+(?:retro\s+)?(?:high|mid|low)\b', 'Air Jordan 1'),
    (r'\bair\s+jordan\s+1\b', 'Air Jordan 1'),
    (r'\bair\s+jordan\s+2\b', 'Air Jordan 2'),
    (r'\bair\s+jordan\s+3\b', 'Air Jordan 3'),
    (r'\bair\s+jordan\s+4\b', 'Air Jordan 4'),
    (r'\bair\s+jordan\s+5\b', 'Air Jordan 5'),
    (r'\bair\s+jordan\s+6\b', 'Air Jordan 6'),
    (r'\bair\s+jordan\s+7\b', 'Air Jordan 7'),
    (r'\bair\s+jordan\s+8\b', 'Air Jordan 8'),
    (r'\bair\s+jordan\s+9\b', 'Air Jordan 9'),
    (r'\bair\s+jordan\s+10\b', 'Air Jordan 10'),
    (r'\bair\s+jordan\s+11\b', 'Air Jordan 11'),
    (r'\bair\s+jordan\s+12\b', 'Air Jordan 12'),
    (r'\bair\s+jordan\s+13\b', 'Air Jordan 13'),
    (r'\bair\s+jordan\s+14\b', 'Air Jordan 14'),
    (r'\bair\s+jordan\s+17\b', 'Air Jordan 17'),
    (r'\bjordan\s+1\s+(?:retro\s+)?(?:high|mid|low)\b', 'Air Jordan 1'),
    (r'\bjordan\s+1\b', 'Air Jordan 1'),
    (r'\bjordan\s+3\b', 'Air Jordan 3'),
    (r'\bjordan\s+4\b', 'Air Jordan 4'),
    (r'\bjordan\s+5\b', 'Air Jordan 5'),
    (r'\bjordan\s+11\b', 'Air Jordan 11'),
    # Dunk
    (r'\bdunk\s+low\b', 'Dunk Low'),
    (r'\bdunk\s+high\b', 'Dunk High'),
    (r'\bdunk\b', 'Dunk'),
    # Air Max
    (r'\bair\s+max\s+1\b', 'Air Max 1'),
    (r'\bair\s+max\s+90\b', 'Air Max 90'),
    (r'\bair\s+max\s+95\b', 'Air Max 95'),
    (r'\bair\s+max\s+97\b', 'Air Max 97'),
    (r'\bair\s+max\s+98\b', 'Air Max 98'),
    (r'\bair\s+max\s+dn\b', 'Air Max DN'),
    (r'\bair\s+max\s+plus\b', 'Air Max Plus'),
    (r'\bair\s+max\s+2013\b', 'Air Max 2013'),
    (r'\bair\s+max\s+2017\b', 'Air Max 2017'),
    # Air Force
    (r'\bair\s+force\s+1\s+(?:low|high|mid)\b', 'Air Force 1'),
    (r'\bair\s+force\s+1\b', 'Air Force 1'),
    # Nike divers
    (r'\bair\s+huarache\b', 'Air Huarache'),
    (r'\bhuarache\s+2k4\b', 'Huarache 2K4'),
    (r'\bair\s+rift\b', 'Air Rift'),
    (r'\bblazers?\s+(?:low|mid|high)\b', 'Blazer'),
    (r'\bblazers?\b', 'Blazer'),
    (r'\bkobe\s+\d+\b', lambda m: f"Kobe {m.group().split()[-1]}"),
    (r'\blebron\s+\d+\b', lambda m: f"LeBron {m.group().split()[-1]}"),
    (r'\bcryoshot\b', 'Cryoshot'),
    (r'\bpegasus\b', 'Pegasus'),
    (r'\bvapormax\b', 'VaporMax'),
    (r'\bfree\s+run\b', 'Free Run'),
    # New Balance
    (r'\bnew\s+balance\s+550\b', 'New Balance 550'),
    (r'\bnew\s+balance\s+574\b', 'New Balance 574'),
    (r'\bnew\s+balance\s+990\b', 'New Balance 990'),
    (r'\bnew\s+balance\s+991\b', 'New Balance 991'),
    (r'\bnew\s+balance\s+992\b', 'New Balance 992'),
    (r'\bnew\s+balance\s+993\b', 'New Balance 993'),
    (r'\bnew\s+balance\s+1006\b', 'New Balance 1006'),
    (r'\bnew\s+balance\s+1906[rd]?\b', 'New Balance 1906'),
    (r'\bnew\s+balance\s+2002[rd]?\b', 'New Balance 2002R'),
    (r'\bnew\s+balance\s+9060\b', 'New Balance 9060'),
    (r'\bnb\s+550\b', 'New Balance 550'),
    (r'\bnb\s+993\b', 'New Balance 993'),
    # Adidas
    (r'\bsamba\b', 'Adidas Samba'),
    (r'\bstan\s+smith\b', 'Stan Smith'),
    (r'\bgazelle\b', 'Adidas Gazelle'),
    (r'\bsupernova\b', 'Adidas Supernova'),
    (r'\badizero\b', 'Adidas Adizero'),
    (r'\bultraboost\b', 'Adidas Ultraboost'),
    (r'\bnmd\b', 'Adidas NMD'),
    (r'\byeezy\s+\d+\b', lambda m: f"Yeezy {m.group().split()[-1]}"),
    (r'\byeezy\b', 'Yeezy'),
    # Asics
    (r'\bgel-?\s*kayano\b', 'Asics Gel-Kayano'),
    (r'\bgel-?\s*lyte\b', 'Asics Gel-Lyte'),
    (r'\bgel-?\s*nimbus\b', 'Asics Gel-Nimbus'),
    (r'\bgel-?\s*1090\b', 'Asics Gel-1090'),
    (r'\bgt-?\s*2160\b', 'Asics GT-2160'),
    # Converse
    (r'\bchuck\s+taylor\b', 'Chuck Taylor'),
    (r'\bconverse\s+\w+\b', lambda m: m.group().title()),
    # Puma
    (r'\bsuede\b', 'Puma Suede'),
    (r'\bclyde\b', 'Puma Clyde'),
    (r'\bspeedcat\b', 'Puma Speedcat'),
    (r'\bpalermo\b', 'Puma Palermo'),
]


def infer_silhouette(title: str, rid: str) -> str | None:
    """Extrait la silhouette depuis le titre ou l'id."""
    text = (title + " " + rid).lower()
    for pattern, result in SILHOUETTE_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            if callable(result):
                return result(m)
            return result
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PATTERNS COLORWAY
# ─────────────────────────────────────────────────────────────────────────────

# Couleurs de base pour extraction heuristique
BASE_COLORS = [
    "White", "Black", "Red", "Blue", "Navy", "Green", "Yellow", "Orange",
    "Purple", "Pink", "Brown", "Grey", "Gray", "Beige", "Cream", "Olive",
    "Coral", "Teal", "Turquoise", "Gold", "Silver", "Tan", "Khaki",
    "Burgundy", "Maroon", "Mint", "Lavender", "Indigo", "Violet", "Cyan",
    "Magenta", "Rose", "Salmon", "Peach", "Ivory", "Sand", "Rust",
    "Crimson", "Scarlet", "Cobalt", "Royal", "Sky", "Lime", "Forest",
    "Smoke", "Stone", "Clay", "Camo", "Multi", "Natural", "Neutral",
    "Wheat", "Sail", "Phantom", "Dark Mocha", "Mocha", "Obsidian",
    "Concord", "Bred", "Chicago", "Panda", "Infrared", "Pistachio",
    "Sesame", "Muslin", "Alabaster", "Anthracite", "Midnight", "Light Bone",
    "Light Smoke", "Summit White", "University Red", "University Blue",
    "University Gold", "Hyper Royal", "Game Royal", "Cool Grey",
    "Wolf Grey", "Dark Grey", "Medium Grey", "Light Grey",
    "Varsity Red", "Varsity Maize", "Varsity Royal",
    "Court Purple", "Field Purple",
    "Volt", "Electric Green", "Chlorophyll",
    "Total Orange", "Team Orange",
    "Metallic Gold", "Metallic Silver", "Chrome",
    "Particle Grey", "Particle Beige",
    "Atmosphere", "Glacier Blue", "Glacier Ice",
    "Cacao Wow", "Archaeo Brown", "Hemp", "Flax",
    "Dutch Blue", "Marina", "Midnight Navy",
    "Gym Red", "Gym Blue",
    "Stadium Green", "Court Green",
    "Lemon Wash", "Lemon Yellow",
    "Fog", "Dune", "Desert", "Cactus", "Sage",
    "Umber", "Sepia", "Taupe",
]

COLOR_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(c) for c in sorted(BASE_COLORS, key=len, reverse=True)) + r')\b',
    re.IGNORECASE
)

# Certains titres contiennent le colorway après un tiret ou "in"
COLORWAY_SUFFIX = re.compile(
    r'(?:[-–]\s*|"\s*|\bin\s+)([A-Z][a-z]+(?:[/ ][A-Z][a-z]+){1,4})\s*(?:$|")',
    re.IGNORECASE
)


def infer_colorway(title: str, rid: str) -> str | None:
    """Extrait le colorway depuis le titre."""
    # 1. Cherche les couleurs connues dans le titre
    matches = COLOR_PATTERN.findall(title)
    if matches:
        # Déduplique en conservant l'ordre
        seen = set()
        unique = []
        for m in matches:
            key = m.lower()
            if key not in seen:
                seen.add(key)
                # Normalise la casse : première lettre majuscule
                unique.append(m.title() if m.islower() else m)
        if unique:
            return "/".join(unique[:4])  # max 4 couleurs

    # 2. Cherche un pattern "X/Y/Z" déjà formaté dans le titre
    slash_match = re.search(r'\b([A-Z][a-z]+(?:/[A-Z][a-z]+){1,3})\b', title)
    if slash_match:
        return slash_match.group(1)

    return None


# ─────────────────────────────────────────────────────────────────────────────
# PATTERNS YEAR
# ─────────────────────────────────────────────────────────────────────────────

def infer_year(title: str, rid: str, date: str) -> int | None:
    """Détermine l'année de sortie."""
    # 1. Depuis la date
    if date and date != "TBD":
        try:
            return int(date[:4])
        except Exception:
            pass

    # 2. Année explicite dans le titre (ex: "2025", "2026")
    year_match = re.search(r'\b(202[0-9]|2030)\b', title + " " + rid)
    if year_match:
        return int(year_match.group(1))

    # 3. Année courante par défaut (releases actives)
    return datetime.now().year


# ─────────────────────────────────────────────────────────────────────────────
# ENRICHISSEMENT WEB (Perplexity / fallback)
# ─────────────────────────────────────────────────────────────────────────────

def enrich_via_web(r: dict) -> dict:
    """
    Tente d'enrichir via une recherche web (nécessite pplx-tool ou requests+API).
    Retourne un dict avec les champs trouvés.
    """
    try:
        import subprocess, json as _json
        sku = r.get("sku") or ""
        title = r.get("title") or ""
        query = sku if sku else title
        query += " sneaker colorway release date"

        payload = _json.dumps({"query": query, "focus": "internet"})
        result = subprocess.run(
            ["pplx-tool", "search"],
            input=payload, capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0:
            data = _json.loads(result.stdout)
            text = data.get("answer", "") + " " + " ".join(
                s.get("snippet", "") for s in data.get("sources", [])[:3]
            )
            enriched = {}
            # Colorway dans la réponse
            if not r.get("colorway"):
                cw_match = re.search(r'colorway[:\s]+([A-Z][a-z]+(?:/[A-Z][a-z]+)+)', text)
                if cw_match:
                    enriched["colorway"] = cw_match.group(1)
            return enriched
    except Exception as e:
        log(f"  ⚠ fallback web échoué : {e}")
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# ENRICHISSEMENT D'UNE RELEASE
# ─────────────────────────────────────────────────────────────────────────────

def enrich_release(r: dict, use_web: bool = False) -> tuple[dict, list]:
    """
    Tente d'enrichir les champs manquants d'une release.
    Retourne (release_enrichie, liste_des_champs_modifiés).
    """
    changes = []
    title = r.get("title") or ""
    rid = r.get("id") or ""
    date = r.get("date") or "TBD"

    # --- Silhouette ---
    if not r.get("silhouette"):
        s = infer_silhouette(title, rid)
        if s:
            r["silhouette"] = s
            changes.append(f"silhouette={s}")

    # --- Colorway ---
    if not r.get("colorway"):
        cw = infer_colorway(title, rid)
        if cw:
            r["colorway"] = cw
            changes.append(f"colorway={cw}")
        elif use_web:
            extra = enrich_via_web(r)
            if extra.get("colorway"):
                r["colorway"] = extra["colorway"]
                changes.append(f"colorway={extra['colorway']} (web)")

    # --- Year ---
    if not r.get("year"):
        y = infer_year(title, rid, date)
        if y:
            r["year"] = y
            changes.append(f"year={y}")

    return r, changes


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Enrichissement automatique releases")
    parser.add_argument("--apply", action="store_true", help="Applique les modifications (sans : dry-run)")
    parser.add_argument("--web", action="store_true", help="Active le fallback web pour le colorway")
    parser.add_argument("--file", default=None, help="Fichier JSON cible (défaut : les deux)")
    parser.add_argument("--verbose", action="store_true", help="Log détaillé")
    args = parser.parse_args()

    files = []
    if args.file:
        files = [os.path.join(ROOT, args.file)]
    else:
        files = [
            os.path.join(ROOT, "releases.json"),
            os.path.join(ROOT, "releases_past.json"),
        ]

    total_enriched = 0

    for fpath in files:
        fname = os.path.basename(fpath)
        if not os.path.exists(fpath):
            log(f"⚠ {fname} introuvable — ignoré")
            continue

        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)

        needs_enrich = [
            r for r in data
            if not r.get("colorway") or not r.get("silhouette") or not r.get("year")
        ]

        if not needs_enrich:
            log(f"✓ {fname} : tous les champs déjà remplis ({len(data)} entrées)")
            continue

        log(f"\n{fname} : {len(needs_enrich)}/{len(data)} entrées à enrichir")

        enriched_count = 0
        for r in data:
            if not r.get("colorway") or not r.get("silhouette") or not r.get("year"):
                before = {
                    "colorway": r.get("colorway"),
                    "silhouette": r.get("silhouette"),
                    "year": r.get("year"),
                }
                r, changes = enrich_release(r, use_web=args.web)
                if changes:
                    enriched_count += 1
                    total_enriched += 1
                    if args.verbose or not args.apply:
                        log(f"  [{r['id']}] → {', '.join(changes)}")
                elif args.verbose:
                    still_missing = [
                        k for k in ["colorway", "silhouette", "year"] if not r.get(k)
                    ]
                    if still_missing:
                        log(f"  [{r['id']}] ✗ manque encore : {', '.join(still_missing)}")

        log(f"  → {enriched_count} entrées enrichies sur {len(needs_enrich)}")

        if args.apply and enriched_count > 0:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            log(f"  ✓ {fname} sauvegardé")

    if not args.apply:
        log(f"\nDry-run terminé — {total_enriched} enrichissements possibles. Relancer avec --apply pour appliquer.")
    else:
        log(f"\n✅ Enrichissement terminé — {total_enriched} champs remplis au total.")

    return total_enriched


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)
