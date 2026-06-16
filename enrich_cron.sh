#!/usr/bin/env bash
# enrich_cron.sh — Pipeline complet d'enrichissement automatique
# =================================================================
# À appeler depuis le cron après un git pull.
# Pipeline :
#   1. git pull (récupère les nouvelles releases)
#   2. enrich_new_releases.py --apply  (remplit colorway/silhouette/year manquants)
#   3. Régénération des pages HTML si des champs ont été enrichis
#   4. git add + commit + push si des fichiers ont changé
#
# Cron recommandé (toutes les 6h) :
#   0 */6 * * * /bin/bash /var/www/sneakerdropfr/enrich_cron.sh >> /var/log/enrich_cron.log 2>&1
#
# Pré-requis :
#   - git configuré avec SSH ou token HTTPS
#   - python3 dans PATH
#   - pip install fastapi uvicorn (pour click_tracker uniquement)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_PREFIX="[enrich_cron]"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
CHANGED=0

log() {
    echo "${LOG_PREFIX} ${TIMESTAMP} $*"
}

cd "$REPO_DIR"
log "=== Démarrage pipeline enrichissement ==="

# ── 1. git pull ──────────────────────────────────────────────────────────────
log "git pull..."
git pull --ff-only 2>&1 | while IFS= read -r line; do log "  git: $line"; done

# ── 2. Enrichissement automatique ───────────────────────────────────────────
log "Enrichissement releases.json + releases_past.json..."
ENRICH_OUTPUT=$(python3 "${REPO_DIR}/enrich_new_releases.py" --apply 2>&1)
echo "$ENRICH_OUTPUT" | while IFS= read -r line; do log "  $line"; done

# Vérifie si des champs ont été remplis
if echo "$ENRICH_OUTPUT" | grep -q "champs remplis au total\." && \
   ! echo "$ENRICH_OUTPUT" | grep -q "0 champs remplis"; then
    CHANGED=1
    log "→ Des champs ont été enrichis"
fi

# ── 3. Régénération des pages HTML si enrichissement ────────────────────────
if [ "$CHANGED" -eq 1 ]; then
    log "Régénération des pages HTML..."
    python3 -c "
import json, sys, os
sys.path.insert(0, '${REPO_DIR}')
os.chdir('${REPO_DIR}')

# Régénération releases.json (actives)
from generate_release_pages import render_page, _load_manual_retailers
import generate_release_pages as grp

with open('releases.json') as f:
    releases = json.load(f)
with open('releases_past.json') as f:
    past = json.load(f)

manual = _load_manual_retailers()
count = 0
for r in releases + past:
    try:
        render_page(r, manual)
        count += 1
    except Exception as e:
        print(f'  ERR {r.get(\"id\")}: {e}')

print(f'  {count} pages régénérées')
" 2>&1 | while IFS= read -r line; do log "  $line"; done
fi

# ── 4. git add + commit + push si changements ───────────────────────────────
if git diff --quiet && git diff --cached --quiet; then
    log "✓ Aucun changement à commiter"
else
    log "Commit + push..."
    git add releases.json releases_past.json sorties/ 2>/dev/null || true
    git commit -m "auto: enrichissement colorway/silhouette/year — $(date '+%Y-%m-%d %H:%M')" 2>&1 | \
        while IFS= read -r line; do log "  git: $line"; done
    git push 2>&1 | while IFS= read -r line; do log "  git: $line"; done
    log "✅ Push effectué"
fi

log "=== Pipeline terminé ==="
