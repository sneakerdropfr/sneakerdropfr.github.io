/*
 * Validation : cards Hype Picks cliquables vers la page détail.
 *
 * Règle métier (2026-05-16) : sur hype-picks.html et le Top Pick de la home,
 * l'image + le titre des cards doivent être enrobés dans un <a> vers
 * /sorties/<id>.html quand la page existe. La logique anti-404 `hasLink`
 * (retailers || buy_url || wtc_url) doit décider de la génération du lien.
 * Les boutons retailers (Awin / BSTN / WhenToCop / Skimlinks) doivent rester
 * intacts, target="_blank", et ne pas être interceptés par le lien article.
 *
 * Run: node tests/test_hype_clickable.js
 */

var fs = require('fs');
var path = require('path');
var ROOT = path.join(__dirname, '..');

function assert(cond, msg) {
  if (!cond) { console.error('FAIL:', msg); process.exitCode = 1; }
  else { console.log('OK:  ', msg); }
}

var hypeHtml = fs.readFileSync(path.join(ROOT, 'hype-picks.html'), 'utf8');
var indexHtml = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

// -- 1. hype-picks.html : renderCard utilise hasLink + articleUrl --
assert(/renderCard[\s\S]{0,1200}?hasLink\s*=\s*\(r\.retailers\s*&&\s*r\.retailers\.length\)\s*\|\|\s*r\.buy_url\s*\|\|\s*r\.wtc_url/.test(hypeHtml),
       'hype-picks.html renderCard utilise hasLink anti-404');
assert(/renderCard[\s\S]{0,1400}?articleUrl\s*=\s*\(r\.id\s*&&\s*hasLink\)\s*\?\s*'\/sorties\/'\s*\+\s*r\.id\s*\+\s*'\.html'\s*:\s*null/.test(hypeHtml),
       'hype-picks.html renderCard construit articleUrl uniquement si id + hasLink');

// -- 2. hype-picks.html : image + titre enrobés dans un <a href articleUrl> --
assert(/renderCard[\s\S]{0,2000}?articleUrl[\s\S]{0,200}?<a href="'\s*\+\s*articleUrl\s*\+\s*'"[^']*?class="drop-card__img-wrap"/.test(hypeHtml),
       'hype-picks.html : image wrap est un <a> vers articleUrl quand dispo');
assert(/renderCard[\s\S]{0,2000}?articleUrl[\s\S]{0,400}?<a href="'\s*\+\s*articleUrl\s*\+\s*'"[^']*?<h3 class="drop-card__title">/.test(hypeHtml),
       'hype-picks.html : titre h3 enrobé dans <a> vers articleUrl quand dispo');

// -- 3. hype-picks.html : boutons retailers conservent target="_blank" --
assert(/href="'\s*\+\s*rt\.url\s*\+\s*'"\s*target="_blank"\s*rel="noopener"/.test(hypeHtml),
       'hype-picks.html : retailers gardent target=_blank rel=noopener');
assert(/href="'\s*\+\s*r\.buy_url\s*\+\s*'"\s*target="_blank"\s*rel="noopener"/.test(hypeHtml),
       'hype-picks.html : buy_url Awin garde target=_blank');
assert(/href="'\s*\+\s*r\.wtc_url\s*\+\s*'"\s*target="_blank"\s*rel="noopener"/.test(hypeHtml),
       'hype-picks.html : wtc_url WhenToCop garde target=_blank');

// -- 4. Skimlinks 302926X179095 préservé --
assert(hypeHtml.indexOf('302926X179095') !== -1,
       'Skimlinks 302926X179095 toujours présent dans hype-picks.html');

// -- 5. index.html renderTopPick utilise hasLink + articleUrl --
assert(/renderTopPick[\s\S]{0,2000}?hasLink\s*=\s*\(r\.retailers\s*&&\s*r\.retailers\.length\)\s*\|\|\s*r\.buy_url\s*\|\|\s*r\.wtc_url/.test(indexHtml),
       'index.html renderTopPick utilise hasLink anti-404');
assert(/renderTopPick[\s\S]{0,2000}?articleUrl\s*=\s*\(r\.id\s*&&\s*hasLink\)\s*\?\s*'sorties\/'\s*\+\s*r\.id\s*\+\s*'\.html'\s*:\s*null/.test(indexHtml),
       'index.html renderTopPick construit articleUrl uniquement si id + hasLink');
assert(/renderTopPick[\s\S]{0,2500}?<a href="'\s*\+\s*articleUrl\s*\+\s*'"[^']*?class="top-pick__img-wrap"/.test(indexHtml),
       'index.html renderTopPick : image wrap enrobé dans <a> quand dispo');
assert(/renderTopPick[\s\S]{0,2500}?<a href="'\s*\+\s*articleUrl\s*\+\s*'"[^']*?<h2 class="top-pick__title">/.test(indexHtml),
       'index.html renderTopPick : titre h2 enrobé dans <a> quand dispo');

// -- 6. index.html renderCard (cards normales home) toujours cliquables --
assert(/renderCard\(r,\s*index\)[\s\S]{0,1500}?hasLink\s*=/.test(indexHtml),
       'index.html renderCard (cards home) conserve hasLink');

// -- 7. Les pages détail attendues pour les hype picks existent réellement --
var releases = JSON.parse(fs.readFileSync(path.join(ROOT, 'releases.json'), 'utf8'));
var COLLABS = ['travis scott','nigel sylvester','off-white','patta','sacai','nocta','bad bunny','union','fragment','clot'];
function score(r) {
  var s = 0;
  if (r.featured) s += 1000;
  var t = (r.title || '').toLowerCase();
  var b = (r.brand || '').toLowerCase();
  if (b.indexOf('jordan') !== -1) s += 40;
  else if (b.indexOf('nike') !== -1) s += 20;
  else if (b.indexOf('adidas') !== -1) s += 15;
  else if (b.indexOf('new balance') !== -1) s += 15;
  for (var i = 0; i < COLLABS.length; i++) if (t.indexOf(COLLABS[i]) !== -1) { s += 50; break; }
  var prem = ['jordan 4','jordan 1','jordan 11','jordan 3','jordan 12','dunk','990','991','2002'];
  for (var j = 0; j < prem.length; j++) if (t.indexOf(prem[j]) !== -1) { s += 25; break; }
  if (r.resell) s += 30;
  return s;
}
var today = new Date(2026, 4, 16); today.setHours(0,0,0,0);
function isFutureOrToday(d) {
  if (!d || d === 'TBD') return true;
  var p = d.split('-');
  return new Date(+p[0], +p[1]-1, +p[2]) >= today;
}
var hypeWithLink = releases.filter(function(r) {
  if (!r.id || r.id.indexOf('test-') === 0) return false;
  if (!isFutureOrToday(r.date)) return false;
  if (score(r) < 90) return false;
  return (r.retailers && r.retailers.length) || r.buy_url || r.wtc_url;
});
assert(hypeWithLink.length > 0,
       'Au moins une hype pick avec hasLink existe dans releases.json (n=' + hypeWithLink.length + ')');
var missingPages = hypeWithLink.filter(function(r) {
  return !fs.existsSync(path.join(ROOT, 'sorties', r.id + '.html'));
});
assert(missingPages.length === 0,
       'Chaque hype pick (hasLink=true) a sa page détail : ' +
       (missingPages.length ? 'manquantes: ' + missingPages.map(function(r){return r.id;}).join(', ') : 'OK'));

// -- 8. Aucune régression sur Skimlinks index.html --
assert(indexHtml.indexOf('302926X179095') !== -1,
       'Skimlinks 302926X179095 toujours présent dans index.html');

if (process.exitCode) {
  console.error('\n>>> Tests hype clickable : échec.');
} else {
  console.log('\n>>> Tous les tests hype clickable passent.');
}
