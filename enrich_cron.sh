#!/usr/bin/env bash
# enrich_cron.sh — Pipeline complet d'enrichissement automatique
# =================================================================
# Pipeline :
#   1. git pull --ff-only  (pour sitemap.xml, sorties/, fichiers locaux UNIQUEMENT)
#      ⚠️  releases.json N'EST PAS géré par git ici — il est lu/écrit via API GitHub
#   2. enrich_new_releases.py --apply  (lit releases.json via API GitHub, push via gh_put)
#   3. Régénération des pages HTML si enrichissement
#   4. git add + commit + push pour les fichiers locaux uniquement (sorties/, sitemap.xml)
#      ⚠️  releases.json EXCLU du git add/commit — géré exclusivement via API GitHub
#
# Cron recommandé (toutes les 6h) :
#   0 */6 * * * /bin/bash /var/www/sneakerdropfr/enrich_cron.sh >> /var/log/enrich_cron.log 2>&1

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

# ── 1. git pull (fichiers locaux uniquement — releases.json géré via API GitHub) ──
log "git pull (fichiers locaux)..."
# On fait un git checkout pour s'assurer que releases.json local ne crée pas de conflit
# releases.json est géré exclusivement via API GitHub — on ignore les conflits locaux
git fetch origin 2>&1 | while IFS= read -r line; do log "  git: $line"; done
git checkout origin/main -- sitemap.xml sorties/ 2>/dev/null || true
# git pull uniquement pour les autres fichiers (pas releases.json)
git stash -- releases.json 2>/dev/null || true
git pull --ff-only 2>&1 | while IFS= read -r line; do log "  git: $line"; done || {
    log "  ⚠ ff-only impossible, reset hard sur origin/main (hors releases.json)"
    git fetch origin
    git reset --hard origin/main
}
# Restaurer releases.json local depuis stash si besoin (mais on ne l'utilisera pas)
git stash pop 2>/dev/null || true

# ── 2. Enrichissement automatique via API GitHub ─────────────────────────────
log "Enrichissement releases.json via API GitHub..."
ENRICH_OUTPUT=$(python3 "${REPO_DIR}/enrich_new_releases.py" --apply 2>&1)
echo "$ENRICH_OUTPUT" | while IFS= read -r line; do log "  $line"; done

# Vérifie si des champs ont été remplis
if echo "$ENRICH_OUTPUT" | grep -q "champs remplis au total\." && \
   ! echo "$ENRICH_OUTPUT" | grep -q "0 champs remplis"; then
    CHANGED=1
    log "→ Des champs ont été enrichis"
fi

# ── 3. Régénération des pages HTML si enrichissement ────────────────────────
# releases.json est relu depuis le fichier local (synchronisé par le script précédent)
# Pour la génération HTML, on utilise le fichier local mis à jour via git pull
if [ "$CHANGED" -eq 1 ]; then
    log "Régénération des pages HTML..."
    python3 -c "
import json, sys, os
sys.path.insert(0, '${REPO_DIR}')
os.chdir('${REPO_DIR}')

from generate_release_pages import render_page, _load_manual_retailers

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

# ── 3.5. Nettoyage des pages orphelines ──────────────────────────────────────
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
        pattern = rf'<url>\s*<loc>https://sneakerdropfr\.fr/sorties/{re.escape(file_id)}\.html</loc>.*?</url>\s*'
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

# ── 4. git add + commit + push (SANS releases.json) ──────────────────────────
# releases.json est géré exclusivement via API GitHub — ne jamais le commiter ici
log "Vérification des changements locaux (sorties/, sitemap.xml, releases_past.json)..."

# S'assurer que releases.json n'est pas dans le staging
git reset HEAD releases.json 2>/dev/null || true
git checkout -- releases.json 2>/dev/null || true

if git diff --quiet sorties/ sitemap.xml releases_past.json 2>/dev/null && \
   git diff --cached --quiet sorties/ sitemap.xml releases_past.json 2>/dev/null; then
    log "✓ Aucun changement local à commiter"
else
    log "Commit + push (sorties/, sitemap.xml, releases_past.json uniquement)..."
    git add sorties/ sitemap.xml releases_past.json 2>/dev/null || true
    git reset HEAD releases.json 2>/dev/null || true  # sécurité supplémentaire
    git commit -m "[skip ci] enrich: colorway/silhouette/year — $(date '+%Y-%m-%d %H:%M')" 2>&1 | \
        while IFS= read -r line; do log "  git: $line"; done
    git push 2>&1 | while IFS= read -r line; do log "  git: $line"; done
    log "✅ Push effectué (releases.json exclu)"
fi

log "=== Pipeline terminé ==="
