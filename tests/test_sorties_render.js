/*
 * Validation : groupement "Disponible aujourd'hui" vs "À venir" sur sorties.html.
 *
 * Approche : on charge sorties.html en tant que texte, on en extrait le bloc
 *            entre les markers de la fonction render(), et on s'assure que les
 *            mots-clés clés y sont (filtre par date, séparation des deux blocs).
 *            Puis on simule la logique sur releases.json et on vérifie que
 *            AJ3 Brazil et AJ1 Low Banned (datés du 16 mai) sont bien dans le
 *            bloc "Disponible aujourd'hui" et JAMAIS dans "À venir" un 16 mai.
 *
 * Run: node tests/test_sorties_render.js
 */

var fs = require('fs');
var path = require('path');
var ROOT = path.join(__dirname, '..');

function assert(cond, msg) {
  if (!cond) {
    console.error('FAIL:', msg);
    process.exitCode = 1;
  } else {
    console.log('OK:  ', msg);
  }
}

// -- 1. Le fichier sorties.html doit contenir le nouveau découpage --
var sortiesHtml = fs.readFileSync(path.join(ROOT, 'sorties.html'), 'utf8');
assert(sortiesHtml.indexOf('releases-grid-today') !== -1,
       'sorties.html contient le grid "Disponible aujourd\'hui"');
assert(sortiesHtml.indexOf('Disponible aujourd’hui') !== -1 || sortiesHtml.indexOf("Disponible aujourd'hui") !== -1,
       'sorties.html contient le label "Disponible aujourd\'hui"');
assert(sortiesHtml.indexOf('today-header') !== -1,
       'sorties.html contient l\'en-tête "today-header"');
assert(sortiesHtml.indexOf('d>=tomorrowMidnight') !== -1,
       'sorties.html filtre upcoming sur d >= tomorrowMidnight (strictement futur)');
assert(sortiesHtml.indexOf('d.getTime()===todayMidnight.getTime()') !== -1,
       'sorties.html sépare dispoToday sur égalité stricte avec todayMidnight');
assert(sortiesHtml.indexOf('302926X179095') !== -1,
       'Skimlinks 302926X179095 toujours présent dans sorties.html');

// -- 2. Réimplémentation locale du filtre, exécutée avec date simulée --
function buildRenderBuckets(releases, now) {
  var todayMidnight = new Date(now); todayMidnight.setHours(0,0,0,0);
  var tomorrowMidnight = new Date(todayMidnight); tomorrowMidnight.setDate(tomorrowMidnight.getDate()+1);
  function parseLocal(str){
    if (!str || str==='TBD') return null;
    var p=str.split('-');
    return p.length===3 ? new Date(parseInt(p[0]),parseInt(p[1])-1,parseInt(p[2])) : null;
  }
  var dispoToday = releases.filter(function(r){
    if (r.raffle) return false;
    var d = parseLocal(r.date);
    return d && d.getTime() === todayMidnight.getTime();
  });
  var upcoming = releases.filter(function(r){
    if (r.raffle) return false;
    if (!r.date || r.date === 'TBD') return true;
    var d = parseLocal(r.date);
    if (!d) return true;
    return d >= tomorrowMidnight;
  });
  var pastReleased = releases.filter(function(r){
    if (r.raffle) return false;
    var d = parseLocal(r.date);
    return d && d < todayMidnight;
  });
  return { dispoToday: dispoToday, upcoming: upcoming, pastReleased: pastReleased };
}

// -- 3. Tester sur releases.json réel, daté du samedi 16 mai 2026 --
var releases = JSON.parse(fs.readFileSync(path.join(ROOT, 'releases.json'), 'utf8'));
var samedi16mai = new Date(2026, 4, 16, 17, 0, 0);
var buckets = buildRenderBuckets(releases, samedi16mai);

var dispoIds   = buckets.dispoToday.map(function(r){ return r.id; });
var upcomingIds= buckets.upcoming.map(function(r){ return r.id; });

assert(dispoIds.indexOf('air-jordan-3-brazil-releases-may-2026') !== -1,
       'AJ3 Brazil (16 mai) est dans "Disponible aujourd\'hui"');
assert(dispoIds.indexOf('air-jordan-1-low-og-banned') !== -1,
       'AJ1 Low OG Banned (16 mai) est dans "Disponible aujourd\'hui"');

assert(upcomingIds.indexOf('air-jordan-3-brazil-releases-may-2026') === -1,
       'AJ3 Brazil (16 mai) N\'EST PAS dans "À venir"');
assert(upcomingIds.indexOf('air-jordan-1-low-og-banned') === -1,
       'AJ1 Low Banned (16 mai) N\'EST PAS dans "À venir"');

// -- 4. Vérifier qu'au moins une paire postérieure au 16 mai EST dans upcoming --
var hasFutureDrop = buckets.upcoming.some(function(r){
  if (!r.date || r.date === 'TBD') return false;
  var p = r.date.split('-');
  var d = new Date(parseInt(p[0]),parseInt(p[1])-1,parseInt(p[2]));
  return d > samedi16mai;
});
assert(hasFutureDrop, 'Au moins une paire strictement future est listée dans "À venir"');

// -- 5. Vérifier que les drops passés (avant 16 mai) ne fuient pas dans upcoming --
var leakedPast = buckets.upcoming.filter(function(r){
  if (!r.date || r.date === 'TBD') return false;
  var p = r.date.split('-');
  var d = new Date(parseInt(p[0]),parseInt(p[1])-1,parseInt(p[2]));
  return d < new Date(2026,4,16);
});
assert(leakedPast.length === 0,
       'Aucune paire passée ne fuit dans "À venir" (n=' + leakedPast.length + ')');

// -- 6. TBD reste dans upcoming (date inconnue = considérée future) --
var tbdInUpcoming = buckets.upcoming.filter(function(r){ return !r.date || r.date==='TBD'; });
console.log('   (info) paires TBD listées dans upcoming :', tbdInUpcoming.length);

// -- 7. Mardi 19 mai 2026 : AJ3 Brazil doit avoir migré hors des deux buckets --
var mardi19mai = new Date(2026, 4, 19, 12, 0, 0);
var b2 = buildRenderBuckets(releases, mardi19mai);
var dispo2 = b2.dispoToday.map(function(r){return r.id;});
var upc2 = b2.upcoming.map(function(r){return r.id;});
assert(dispo2.indexOf('air-jordan-3-brazil-releases-may-2026') === -1,
       'mardi 19 mai : AJ3 Brazil n\'est plus "Disponible aujourd\'hui"');
assert(upc2.indexOf('air-jordan-3-brazil-releases-may-2026') === -1,
       'mardi 19 mai : AJ3 Brazil n\'est plus dans "À venir"');

// -- 8. Lundi 18 mai 2026 : NB 991v2 (20 mai) doit être dans upcoming, pas dans today --
var lundi18mai = new Date(2026, 4, 18, 9, 0, 0);
var b3 = buildRenderBuckets(releases, lundi18mai);
var b3Upc = b3.upcoming.map(function(r){return r.id;});
var nb991 = releases.find(function(r){ return /991v2/i.test(r.title||'') && /balsam|grey/i.test(r.title||''); });
if (nb991) {
  assert(b3Upc.indexOf(nb991.id) !== -1,
         'lun 18 mai : NB 991v2 Made in UK Grey Balsam dans upcoming');
}

// -- 9. Past releases : cards cliquables vers la page détail quand hasLink + id --
var indexHtml = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
assert(indexHtml.indexOf('302926X179095') !== -1,
       'Skimlinks 302926X179095 toujours présent dans index.html');
assert(/renderPastGrid[\s\S]*?hasLink\s*=\s*\(r\.retailers/.test(indexHtml),
       'index.html renderPastGrid utilise hasLink (anti-404)');
assert(/renderPastGrid[\s\S]*?articleUrl\s*=\s*\(r\.id\s*&&\s*hasLink\)/.test(indexHtml),
       'index.html renderPastGrid construit articleUrl uniquement si id + hasLink');

assert(/renderPastGrid[\s\S]*?hasLink\s*=\s*\(r\.retailers/.test(sortiesHtml),
       'sorties.html renderPastGrid utilise hasLink (anti-404)');

// -- 10. Past JSON : chaque id doit pointer vers un fichier sortie qui existe --
var pastJson = JSON.parse(fs.readFileSync(path.join(ROOT, 'releases_past.json'), 'utf8'));
var missing = pastJson.filter(function(r){
  if (!r.id) return false;
  return !fs.existsSync(path.join(ROOT, 'sorties', r.id + '.html'));
});
assert(missing.length === 0,
       'releases_past.json : tous les id correspondent à une page détail (manquants: ' +
       missing.map(function(r){return r.id;}).join(', ') + ')');

// -- 11. Index "Drops de la semaine" : tri ascendant + filtrage image --
assert(/Tri croissant par date dans la semaine/.test(indexHtml) ||
       /sort\(function\(a,\s*b\)\s*{[\s\S]{0,150}?return\s+da\s*-\s*db/.test(indexHtml),
       'index.html applique un tri croissant dans renderWeeklyDrops');
assert(/Exclure les cards sans image utilisable/.test(indexHtml) ||
       /filter\(function\(r\)\s*{\s*return\s+r\.image_url/.test(indexHtml),
       'index.html exclut les cards sans image utilisable dans renderWeeklyDrops');

// -- 12. Badge "isSoon" recalibré sur semaine en cours (pas 7j glissants) --
assert(/function isSoon[\s\S]{0,400}?daysFromMon/.test(indexHtml),
       'index.html isSoon utilise la semaine lundi-dimanche (daysFromMon)');
assert(/function isSoon[\s\S]{0,400}?daysFromMon/.test(sortiesHtml),
       'sorties.html isSoon utilise la semaine lundi-dimanche (daysFromMon)');

if (process.exitCode) {
  console.error('\n>>> Des tests ont échoué.');
} else {
  console.log('\n>>> Tous les tests render passent.');
}
