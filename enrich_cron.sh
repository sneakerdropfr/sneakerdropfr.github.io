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
        render_page(r, releases + past)
        count += 1
    except Exception as e:
        print(f'  ERR {r.get(\"id\")}: {e}')

print(f'  {count} pages régénérées')
" 2>&1 | while IFS= read -r line; do log "  $line"; done
fi

# ── 3.5. Nettoyage des pages orphelines (sans entrée dans releases.json/releases_past.json) ──
log "Nettoyage des pages orphelines..."
ORPHAN_OUTPUT=$(python3 -c "
import json, os, glob, re

repo = '${REPO_DIR}'
releases = json.load(open(f'{repo}/releases.json'))
try:
    past = json.load(open(f'{repo}/releases_past.json'))
except FileNotFoundError:
    past = []

valid_ids = {r['id'] for r in releases} | {r['id'] for r in past}

html_files = glob.glob(f'{repo}/sorties/*.html')
orphans = []
for f in html_files:
    file_id = os.path.basename(f).replace('.html', '')
    if file_id not in valid_ids:
        orphans.append(f)

if orphans:
    sitemap_path = f'{repo}/sitemap.xml'
    sitemap = open(sitemap_path, encoding='utf-8').read()
    for f in orphans:
        os.remove(f)
        file_id = os.path.basename(f).replace('.html', '')
        pattern = rf'<url>\\s*<loc>https://sneakerdropfr\\.fr/sorties/{re.escape(file_id)}\\.html</loc>.*?</url>\\s*'
        sitemap = re.sub(pattern, '', sitemap, flags=re.DOTALL)
    open(sitemap_path, 'w', encoding='utf-8').write(sitemap)
    print(f'{len(orphans)} pages orphelines supprimées + sitemap nettoyé')
    CHANGED_MARKER = 1
else:
    print('Aucune page orpheline')
    CHANGED_MARKER = 0
print(f'__CHANGED__{CHANGED_MARKER}')
" 2>&1)
echo "$ORPHAN_OUTPUT" | grep -v "__CHANGED__" | while IFS= read -r line; do log "  $line"; done
if echo "$ORPHAN_OUTPUT" | grep -q "__CHANGED__1"; then
    CHANGED=1
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
