# RÉCAP SESSION — SneakerDropFR — 02/06/2026

## Contexte de départ

**Problème signalé :** La recherche "jordan 4" retournait Air Jordan 40, Air Jordan 4RM, Air Jordan 3, Air Jordan 11, Air Jordan 13 — résultats totalement parasites.

**État initial :**
- `index.html` : fix word boundary "AVANT seulement" sans fermeture (appliqué en session précédente mais insuffisant)
- `releases_past.json` : 180 paires, dont AJ40/4RM/articles de blog pollulant la recherche
- Badge "DISPO BSTN" affiché même sur paires archivées (date passée)

---

## Commits de la session (chronologique)

| Commit | Fichier | Description |
|---|---|---|
| `c30ae2be` | `index.html` | Word boundary strict avant ET après — suppression du `indexOf` direct |
| `d1359e80` | `releases_past.json` | Suppression 16 paires (AJ40/4RM/articles) + nettoyage titres (180→164) |
| `010e0558` | `index.html` | Badge DISPO BSTN conditionnel — uniquement si date >= aujourd'hui |

---

## Fix 1 — Word boundary strict (index.html)

### Cause racine
La ligne `if (haystackMain.indexOf(q) !== -1) return true;` bypassait **tout** le filtre word boundary. "jordan 4" était trouvé dans "air jordan 40" par indexOf direct → retour immédiat `true` sans tester le boundary.

De plus, la regex précédente n'avait pas de boundary **après** le mot :
```js
// AVANT (insuffisant) — boundary avant seulement
new RegExp('(^|[\\s\\-\'"_/])' + escaped, 'i')
```

### Fix appliqué
```js
// APRÈS — suppression du indexOf direct, boundary strict AVANT + APRÈS
return words.every(function(w){
  var escaped = w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  // Chiffre final : accepte "v" suivi d'un chiffre (990v6) mais pas autre chose
  var after = /\d$/.test(w) ? '($|[\\s\\-\'"_/)]|v(?=[0-9]))' : '($|[\\s\\-\'"_/)])';
  var re = new RegExp('(^|[\\s\\-\'"_/(])' + escaped + after, 'i');
  return re.test(haystackMain);
});
```

### Règles de la regex
- **Boundary AVANT** : `(^|[\s\-'"_/(])` — début de chaîne ou séparateur
- **Boundary APRÈS** — deux cas :
  - Si le mot finit par un **chiffre** : accepte fin/séparateur OU `v` suivi d'un chiffre (pour "990v6"), mais rejette chiffre collé ("40") et lettre collée ("4RM")
  - Si le mot finit par une **lettre** : fin/séparateur uniquement
- Le `indexOf(q)` direct est **supprimé** — il bypassait tout

### Tests validés (28/28 ✅)
| Query | Attendu | Résultat |
|---|---|---|
| "jordan 4" → "Air Jordan 4 Toro Bravo" | MATCH | ✅ |
| "jordan 4" → "Air Jordan 40" | NO | ✅ |
| "jordan 4" → "Air Jordan 4RM" | NO | ✅ |
| "jordan 4" → "Air Jordan 4rm Low" | NO | ✅ |
| "jordan 1" → "Air Jordan 1 Low" | MATCH | ✅ |
| "jordan 1" → "Air Jordan 11 Low" | NO | ✅ |
| "990" → "New Balance 990v6" | MATCH | ✅ |
| "990" → "New Balance 9906" | NO | ✅ |
| "toro" → "Air Jordan 4 Toro Bravo" | MATCH | ✅ |
| "toro" → "Nike ACG Baltoro" | NO | ✅ |
| "air max 90" → "Nike Air Max 900" | NO | ✅ |

---

## Fix 2 — releases_past.json (180 → 164 paires)

### Paires supprimées (16)
**Basket performance (AJ40/4RM) :**
- AIR JORDAN 40, AIR JORDAN 40 ASW, AIR JORDAN 40 SL
- AIR JORDAN 4RM, AIR JORDAN 4 RM
- WMNS AIR JORDAN 4 RM, X PARIS SAINT-GERMAIN AIR JORDAN 4 RM

**Titres sales (RELEASES SUMMER/HOLIDAY) :**
- AIR JORDAN 1 LOW OG "SAIL" RELEASES SUMMER 2026
- OREGON DUCKS X NIKE AIR FORCE 1 LOW PES RELEASES HOLIDAY 2026
- Supreme x Martine Rose x Nike Dunk Low Releases Holiday 2026

**Articles de blog / faux contenus :**
- AVAVAV COMBINES SANDALS & SNEAKERS FOR THEIR ADIDAS MEGARIDE PACK
- La Jellyfish de chez Adidas dans un coloris Green Brown
- NIKE GIVES THE AIR MAX 95 A MULTICOLOR WOVEN UPGRADE FOR SUMMER 2026
- Nike's Next Book 2 Pays Tribute to the Iconic Sedona McDonald's
- THE MANDALORIAN & GROGU HAVE THEIR OWN ADIDAS EVO SL ATR, AVAILABLE NOW
- UNE NOUVELLE ACTION BRONSON X NEW BALANCE 1890 « PLANET FROG » À VENIR

### Titres nettoyés (1)
- "Jason Kidd's Nike Zoom Flight 5 Returns Spring 2027" → "Jason Kidd's Nike Zoom Flight 5"

### État actuel
- **164 paires** propres dans releases_past.json
- ⚠️ 93 paires ont encore une date TBD (vraies sneakers avec image/prix) — elles viennent du catalogue BSTN sans date confirmée. À terme : déplacer sur bstn-deals.html uniquement. Non traitées cette session.

---

## Fix 3 — Badge DISPO BSTN conditionnel (index.html)

### Cause racine
Dans la fonction `filterBySearch`, les cartes de résultats affichaient le badge "DISPO BSTN" dès qu'un `buy_url` était présent — sans vérifier si la paire était encore à venir.

Les paires archivées (ex: AJ12 Bloodline sorti le 23/05, SB Dunk Green Patent sorti le 31/12) affichaient le badge alors qu'elles ne sont plus disponibles.

### Fix appliqué
```js
// Badge DISPO BSTN : uniquement pour paires à venir (date >= aujourd'hui)
var isFuture = r.date && r.date !== 'TBD' && r.date >= new Date().toISOString().slice(0,10);
var badge = r.stock === 'rupture'
  ? '<span class="src__badge src__badge--rupture">Rupture</span>'
  : (r.buy_url && isFuture ? '<span class="src__badge src__badge--dispo">Dispo BSTN</span>' : '');
```

---

## État après session

### GitHub — fichiers modifiés
| Fichier | État |
|---|---|
| `index.html` | ✅ Pushé — word boundary strict + badge fix |
| `releases_past.json` | ✅ Pushé — 164 paires propres |

### État releases
- `releases.json` : 50 paires actives (inchangé)
- `releases_past.json` : 164 paires (était 180)
- `weekly_data.json` : semaine 1-7 juin 2026, 16 drops (inchangé)

### Recherche — Comportement attendu après déploiement
| Query | Résultat attendu |
|---|---|
| "jordan 4" | AJ4 uniquement (Toro, Military, Bred, etc.) |
| "jordan 1" | AJ1 uniquement (Low, High, OG, Travis Scott) |
| "jordan 11" | AJ11 uniquement |
| "dunk" | Nike Dunk (tous colorways) |
| "990" | New Balance 990 (990v6 inclus) |
| Badge archives | Plus de DISPO BSTN sur paires sorties |

---

## Points restants (non traités)

1. **93 TBD dans releases_past.json** — vraies sneakers sans date (catalogue BSTN générique). Règle : doivent aller sur bstn-deals.html uniquement, pas dans la recherche globale.
2. **Vérification live post-déploiement** — GitHub Pages déploie en ~1-2 min. Test à faire manuellement sur sneakerdropfr.fr.

---

## Notes techniques à retenir

### Word boundary regex (JS)
```js
// Mot finissant par chiffre
'(^|[\\s\\-\'"_/(])' + escaped + '($|[\\s\\-\'"_/)]|v(?=[0-9]))'
// Mot finissant par lettre  
'(^|[\\s\\-\'"_/(])' + escaped + '($|[\\s\\-\'"_/)])'
```

### haystack de recherche
- Inclut : titre + marque + SKU + colorway
- Exclut : ID brut (pour éviter "aj1" → "aj11")
- Sources : releases.json (50) + releases_past.json (164) = 214 paires au total

### Badge conditionnel
- `isFuture = date && date !== 'TBD' && date >= today_ISO`
- Condition ajoutée en plus du `buy_url` existant
