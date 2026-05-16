/*
 * Validation : aucune card produit ne doit afficher le fallback emoji 👟 violet
 * dans les listings publics (Drops semaine, Prochaines sorties, Hype Picks,
 * Past releases, Search). Le placeholder doit être inaccessible côté listing
 * et l'onerror doit masquer la card complète, pas la remplacer par l'emoji.
 *
 * Run: node tests/test_image_fallback.js
 */

var fs = require('fs');
var path = require('path');
var ROOT = path.join(__dirname, '..');

function assert(cond, msg) {
  if (!cond) { console.error('FAIL:', msg); process.exitCode = 1; }
  else { console.log('OK:  ', msg); }
}
function read(p) { return fs.readFileSync(path.join(ROOT, p), 'utf8'); }

// -- 1. Le helper global sdfHideBrokenCard est défini dans chaque page listing.
['index.html','sorties.html','hype-picks.html','deals.html'].forEach(function(p){
  var h = read(p);
  assert(/function sdfHideBrokenCard/.test(h),
         p + ' définit sdfHideBrokenCard');
  assert(/window\.sdfHideBrokenCard\s*=\s*sdfHideBrokenCard/.test(h),
         p + ' expose window.sdfHideBrokenCard');
});

// -- 2. Le pattern d'emoji 👟 ne doit plus apparaître dans les onerror des listings.
['index.html','sorties.html','hype-picks.html','deals.html'].forEach(function(p){
  var h = read(p);
  // L'ancien handler remplaçait le parent par <div class=drop-card__img-placeholder>👟</div>
  assert(!/onerror=[^>]*drop-card__img-placeholder[^>]*\xf0\x9f\x91\x9f/.test(h),
         p + ' n\'utilise plus le fallback inline emoji 👟 dans onerror');
});

// -- 3. Chaque renderer de listing utilise sdfHideBrokenCard dans onerror.
function countOnerror(file, pattern) {
  var h = read(file);
  var re = new RegExp(pattern, 'g');
  return (h.match(re) || []).length;
}
assert(countOnerror('index.html', 'window\\.sdfHideBrokenCard') >= 4,
       'index.html branche sdfHideBrokenCard sur plusieurs onerror (renderCard, top-pick, past, search)');
assert(countOnerror('sorties.html', 'window\\.sdfHideBrokenCard') >= 2,
       'sorties.html branche sdfHideBrokenCard sur renderCard et past');
assert(countOnerror('hype-picks.html', 'window\\.sdfHideBrokenCard') >= 1,
       'hype-picks.html branche sdfHideBrokenCard');
assert(countOnerror('deals.html', 'window\\.sdfHideBrokenCard') >= 1,
       'deals.html branche sdfHideBrokenCard');

// -- 4. Filtre "card sans image_url" appliqué dans tous les listings.
var indexHtml = read('index.html');
assert(/filtered\s*=\s*filtered\.filter\(function\(r\)\s*\{[\s\S]{0,80}r\.image_url/.test(indexHtml),
       'index.html upcoming-grid filtre les cards sans image_url');
assert(/filter\(function\(r\)\s*\{\s*return\s+r\.image_url/.test(indexHtml),
       'index.html applique au moins un filtre image_url (weekly + autres)');

var sortiesHtml = read('sorties.html');
assert(/hasUsableImage[\s\S]{0,40}r\.image_url/.test(sortiesHtml) ||
       /brandFilter[\s\S]{0,160}image_url/.test(sortiesHtml),
       'sorties.html filtre brandFilter intègre hasUsableImage(image_url)');

var hypeHtml = read('hype-picks.html');
assert(/filtered\s*=\s*filtered\.filter\(function\(r\)\s*\{[\s\S]{0,80}r\.image_url/.test(hypeHtml),
       'hype-picks.html filtre les cards sans image_url');

// -- 5. Les paires affectées doivent toutes avoir un image_url non-vide,
//       même si on s'attend à ce que le browser puisse échouer dessus
//       (l'onerror est notre garde-fou).
var releases = JSON.parse(read('releases.json'));
var byId = {};
releases.forEach(function(r){ byId[r.id] = r; });
[
  'aj3-worlds-best-dad-2026',
  'air-griffey-max-1-2026',
  'new-balance-abzorb-5030-grey-days',
  'new-balance-abzorb-2000-grey-days',
  'bluetile-nike-sb-dunk-low',
  'nike-ja-3-let-me-be-ja',
].forEach(function(id){
  var r = byId[id];
  assert(r && r.image_url && String(r.image_url).trim() !== '',
         id + ' a un image_url non-vide dans releases.json');
});

// -- 6. Les URLs sneakernews.com/wp-content/.../*.jpg connues comme 404 ont été
//       remplacées pour les 6 paires affectées.
var BROKEN_URL_PATTERNS = [
  /sneakernews\.com\/wp-content\/uploads\/2026\/04\/bluetile-nike-sb-dunk-low-iq1323-001\.jpg/,
  /sneakernews\.com\/wp-content\/uploads\/2026\/04\/nike-ja-3-let-me-be-ja-hf2793-702\.jpg/,
  /sneakernews\.com\/wp-content\/uploads\/2026\/03\/nike-air-griffey-max-1-freshwater-dd8558-100-2026\.jpg/,
  /sneakernews\.com\/wp-content\/uploads\/2026\/05\/air-jordan-3-worlds-best-dad-IF4396-103\.jpg/,
  /statics\.whentocop\.fr\/drops\/20252\/picture\/000000_New-Balance-ABZORB-5030/,
  /statics\.whentocop\.fr\/drops\/20252\/picture\/000000_New-Balance-ABZORB-2000/,
];
var raw = read('releases.json');
BROKEN_URL_PATTERNS.forEach(function(rx, i){
  assert(!rx.test(raw),
         'releases.json ne contient plus l\'URL cassée #' + (i+1) + ' (' + rx.source.slice(0,80) + ')');
});

// -- 7. Le marqueur Skimlinks 302926X179095 est préservé partout.
['index.html','sorties.html','hype-picks.html','deals.html'].forEach(function(p){
  var h = read(p);
  // Skimlinks attendu sur index/sorties uniquement (vérifié dans test_sorties_render),
  // mais on s'assure de ne pas l'avoir retiré accidentellement de ces deux fichiers.
  if (p === 'index.html' || p === 'sorties.html') {
    assert(h.indexOf('302926X179095') !== -1,
           p + ' contient toujours le script Skimlinks 302926X179095');
  }
});

if (process.exitCode) {
  console.error('\n>>> Des tests ont échoué.');
} else {
  console.log('\n>>> Tous les tests image-fallback passent.');
}
