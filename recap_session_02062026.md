# RÉCAP SESSION — SneakerDropFR — 02/06/2026 (complète)

## Contexte de départ

**Problème signalé :** "la recherche jordan 4 affiche tout et n'importe quoi"
La recherche retournait : Air Jordan 40, Air Jordan 4RM, Air Jordan 3 Brazil, Air Jordan 11, Air Jordan 13, prix corrompus "209 [SneakerDrop FR](https://...)", badge DISPO BSTN sur archives.

---

## Fix 1 — Word boundary strict dans index.html

### Commits : `c30ae2be` + `010e0558`

### Cause racine
Deux bugs indépendants dans `filterBySearch()` :

1. `haystackMain.indexOf(q) !== -1` → bypassait TOUT le filtre word boundary. "jordan 4" matchait "jordan 40" via indexOf direct avant même d'arriver à la regex.
2. La regex n'avait pas de boundary **après** le mot : `(^|[\s\-'"_/])` + mot → "4" matchait "40", "4RM".

### Fix appliqué (index.html)
```javascript
// SUPPRIMÉ : if (haystackMain.indexOf(q) !== -1) return true;
// SUPPRIMÉ : if (q.length >= 4 && haystackFull.indexOf(q) !== -1) return true;

return words.every(function(w){
  var escaped = w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  // Chiffre final : accepte "v" suivi d'un chiffre (990v6) mais pas "40" ni "4RM"
  var after = /\d$/.test(w) ? '($|[\\s\\-\'"_/)]|v(?=[0-9]))' : '($|[\\s\\-\'"_/)])';
  var re = new RegExp('(^|[\\s\\-\'"_/(])' + escaped + after, 'i');
  return re.test(haystackMain);
});
```

### Règles de la regex
- **Boundary AVANT** : `(^|[\s\-'"_/(])` — début de chaîne ou séparateur
- **Boundary APRÈS** :
  - Mot finit par **chiffre** : accepte fin/séparateur ou `v` suivi d'un chiffre (990v6), rejette chiffre collé (40) et lettre collée (4RM)
  - Mot finit par **lettre** : fin/séparateur uniquement
- `indexOf` direct complètement supprimé

### Résultat vérifié live
- "jordan 4" → **6 résultats**, uniquement AJ4 (Toro Bravo, Flight Club, Pearl Pink, Love Letter, Nigel, Tatum 4)
- AJ40, 4RM, AJ3, AJ11, AJ13 → tous disparus ✅

### Fix badge DISPO BSTN (commit `010e0558`)
```javascript
var isFuture = r.date && r.date !== 'TBD' && r.date >= new Date().toISOString().slice(0,10);
var badge = r.stock === 'rupture'
  ? '<span class="src__badge src__badge--rupture">Rupture</span>'
  : (r.buy_url && isFuture ? '<span class="src__badge src__badge--dispo">Dispo BSTN</span>' : '');
```
Badge conditionnel : ne s'affiche plus sur les paires avec date passée.

---

## Fix 2 — releases_past.json (180 → 164 paires)

### Commit : `d1359e80`

### Paires supprimées (16)
**Basket performance (AJ40/4RM) :**
- AIR JORDAN 40, AIR JORDAN 40 ASW, AIR JORDAN 40 SL
- AIR JORDAN 4RM, AIR JORDAN 4 RM
- WMNS AIR JORDAN 4 RM, X PARIS SAINT-GERMAIN AIR JORDAN 4 RM

**Titres sales :**
- AIR JORDAN 1 LOW OG "SAIL" RELEASES SUMMER 2026
- OREGON DUCKS X NIKE AIR FORCE 1 LOW PES RELEASES HOLIDAY 2026
- Supreme x Martine Rose x Nike Dunk Low Releases Holiday 2026

**Articles de blog / faux contenus :**
- AVAVAV COMBINES SANDALS & SNEAKERS (Adidas Megaride)
- La Jellyfish de chez Adidas dans un coloris Green Brown
- NIKE GIVES THE AIR MAX 95 A MULTICOLOR WOVEN UPGRADE FOR SUMMER 2026
- Nike's Next Book 2 Pays Tribute to the Iconic Sedona McDonald's
- THE MANDALORIAN & GROGU HAVE THEIR OWN ADIDAS EVO SL ATR
- UNE NOUVELLE ACTION BRONSON X NEW BALANCE 1890 « PLANET FROG » À VENIR

### ⚠️ Point restant non traité
**93 paires TBD** subsistent dans releases_past.json — vraies sneakers avec image/prix mais sans date confirmée (catalogue BSTN générique). Règle : doivent aller sur bstn-deals.html uniquement. Non traitées cette session, à faire dans une prochaine.

---

## Cron 17de7fe5 — Sync dates/prix WhenToCop (exécuté manuellement)

### Commits : `48f3e9c4` (releases.json) + `bfabf747` (releases_snapshot.json)

Le cron a escaladé car browser_task indisponible dans son environnement. Exécuté manuellement en 6 lots parallèles.

### 22 changements de dates appliqués
Principalement des corrections `2026-06-01 → 2026-05-31` pour les sorties déjà passées :
- Nike Air Max 90 Infrared, Adidas Adizero Prime X Evo, Nike Pegasus Premium SP
- Asics : Gel-NYC 2.0, GT-2160, Gel-NYC Khaki, Gel-1130, Gel-Quantum, Gel-Cumulus, Gel-NYC Cocoa
- New Balance : MT10T Fire Cracker, MT10T Raincloud, 5030, 1906L Rosewood
- Adidas : Believe That 1 x2, Adizero Evo SL EXO, Adizero Evo SL WMNS
- Dates avancées : Adidas Tangum/SC Premiere/Powerphase → 05/06, Nike Mind 001 → 04/06

### 0 paire nouvellement datée depuis TBD → pas d'enrichissement retailers déclenché

---

## Cron ac02b788 — Enrichissement retailers
Terminé silencieusement : aucune paire nouvellement datée détectée vs snapshot → comportement normal.

---

## TikTok auto-post (question posée, non implémenté)
**Verdict : impossible via script** — API TikTok Content Posting réservée aux apps approuvées, pas accessible pour compte individuel.
**Options proposées pour la prochaine session :**
1. Script de préparation automatique → slides PNG + caption dans un zip/Telegram
2. **Bot Telegram → envoie slides + caption directement sur OWNER_CHAT_ID 974133940** (recommandé)
3. Upload manuel via TikTok Creator Portal

---

## État final GitHub après session

| Fichier | Commit | Changement |
|---|---|---|
| `index.html` | `c30ae2be` | Word boundary strict (suppression indexOf) |
| `index.html` | `010e0558` | Badge DISPO BSTN conditionnel (isFuture) |
| `releases_past.json` | `d1359e80` | 180 → 164 paires (AJ40/4RM/articles supprimés) |
| `releases.json` | `48f3e9c4` | 22 dates corrigées via WTC |
| `releases_snapshot.json` | `bfabf747` | Snapshot post-cron |
| `recap_session_02062026.md` | `dd2b114d` | Récap intermédiaire |

---

## État releases

| Fichier | Paires | Notes |
|---|---|---|
| `releases.json` | 50 actives | Dates WTC à jour au 02/06 |
| `releases_past.json` | 164 | Propre sauf 93 TBD à déplacer |
| `weekly_data.json` | 16 drops | Semaine 1-7 juin 2026 |
| `releases_snapshot.json` | 50 entrées | Snapshot cron ac02b788 |

---

## Recherche — État final

| Query | Résultat |
|---|---|
| "jordan 4" | 6 résultats — AJ4 uniquement ✅ |
| "jordan 40" / "4rm" | 0 résultat ✅ |
| "dunk" | Tous Nike Dunk ✅ |
| Badge DISPO BSTN | Uniquement sur paires à venir ✅ |

---

## Notes techniques critiques à retenir

### Haystack de recherche
- Inclut : titre + marque + SKU + colorway
- Exclut : ID brut (évite aj1 → aj11)
- Sources : releases.json (50) + releases_past.json (164) = 214 paires

### Word boundary regex (JS)
```js
// Mot finissant par chiffre
'(^|[\\s\\-\'"_/(])' + escaped + '($|[\\s\\-\'"_/)]|v(?=[0-9]))'
// Mot finissant par lettre
'(^|[\\s\\-\'"_/(])' + escaped + '($|[\\s\\-\'"_/)])'
```

### Badge conditionnel
```js
var isFuture = r.date && r.date !== 'TBD' && r.date >= new Date().toISOString().slice(0,10);
```

---

## Prochaine session — Actions prioritaires

1. **93 TBD dans releases_past.json** → à déplacer sur bstn-deals.html ou supprimer
2. **Bot Telegram → envoi slides TikTok** sur OWNER_CHAT_ID (974133940) chaque semaine
3. Vérification globale recherche sur d'autres requêtes (jordan 1, jordan 11, air max 1, etc.)
