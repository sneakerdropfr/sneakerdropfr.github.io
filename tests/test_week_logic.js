/*
 * Validation script for week-range / "Prochaines sorties" date logic.
 *
 * Context (bug fix 2026-05-16):
 *  1. "Drops de la semaine" on index.html must cover the current ISO-ish week
 *     (Monday → Sunday local), without flipping to next week until Monday 00:00.
 *  2. "Prochaines sorties" (sorties.html and home-page upcoming grid) must list
 *     strictly-future drops — today's drops belong to "Drops de la semaine",
 *     not the upcoming list.
 *
 * Run with: node tests/test_week_logic.js
 */

function assert(cond, msg) {
  if (!cond) {
    console.error('FAIL:', msg);
    process.exitCode = 1;
  } else {
    console.log('OK:  ', msg);
  }
}

function fmtFR(d) {
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
}

function weekRange(now) {
  var day = now.getDay();
  var daysFromMon = day === 0 ? 6 : day - 1;
  var monday = new Date(now); monday.setDate(now.getDate() - daysFromMon); monday.setHours(0,0,0,0);
  var sunday = new Date(monday); sunday.setDate(monday.getDate() + 6); sunday.setHours(23,59,59,999);
  var nextMonday = new Date(monday); nextMonday.setDate(monday.getDate() + 7);
  return { monday: monday, sunday: sunday, nextMonday: nextMonday };
}

function parseISO(str) {
  var p = str.split('-');
  return new Date(parseInt(p[0]), parseInt(p[1]) - 1, parseInt(p[2]));
}

// ---- Test scenario : samedi 16 mai 2026 17h00 Europe/Paris ----
var now = new Date(2026, 4, 16, 17, 0, 0); // mois = 4 = mai
var wr = weekRange(now);

assert(fmtFR(wr.monday) === '11 mai',  'monday is 11 mai (got ' + fmtFR(wr.monday) + ')');
assert(fmtFR(wr.sunday) === '17 mai',  'sunday is 17 mai (got ' + fmtFR(wr.sunday) + ')');
assert(wr.nextMonday.getDate() === 18, 'nextMonday = 18 mai');
assert(now < wr.nextMonday,            'now (sam 16) < nextMonday (18) -> badge stays on current week');

// Simulate the "thisWeek" filter on releases
var releases = [
  { title: 'AJ3 Brazil',         date: '2026-05-16' }, // aujourd'hui
  { title: 'AJ1 Low Banned',     date: '2026-05-16' },
  { title: 'NB 991v2 Made in UK',date: '2026-05-20' }, // semaine suivante
  { title: 'AM90 Hypervenom',    date: '2026-05-13' }, // début de semaine, déjà passé
  { title: 'AJ4 Sept',           date: '2026-09-25' },
  { title: 'TBD pair',           date: 'TBD' },
];

function inThisWeek(r) {
  if (!r.date || r.date === 'TBD') return false;
  var d = parseISO(r.date);
  return d >= wr.monday && d <= wr.sunday;
}
var thisWeek = releases.filter(inThisWeek).map(function(r){return r.title;});
assert(thisWeek.length === 3, '3 pairs in this week, got ' + thisWeek.length + ' (' + thisWeek.join(', ') + ')');
assert(thisWeek.indexOf('AJ3 Brazil') !== -1,      'AJ3 Brazil in current week');
assert(thisWeek.indexOf('AJ1 Low Banned') !== -1,  'AJ1 Low Banned in current week');
assert(thisWeek.indexOf('AM90 Hypervenom') !== -1, 'AM90 Hypervenom (lun 13 mai, passé) in current week');
assert(thisWeek.indexOf('NB 991v2 Made in UK') === -1, 'NB 991v2 (20 mai) NOT in current week');

// "Prochaines sorties" = strictement futur (today excluded)
var todayMidnight = new Date(now); todayMidnight.setHours(0,0,0,0);
function isStrictlyFuture(r) {
  if (!r.date || r.date === 'TBD') return true;
  var d = parseISO(r.date);
  return d > todayMidnight;
}
var upcoming = releases.filter(isStrictlyFuture).map(function(r){return r.title;});
assert(upcoming.indexOf('AJ3 Brazil') === -1,     'AJ3 Brazil (today) NOT in upcoming');
assert(upcoming.indexOf('AJ1 Low Banned') === -1, 'AJ1 Low Banned (today) NOT in upcoming');
assert(upcoming.indexOf('AM90 Hypervenom') === -1,'AM90 Hypervenom (passé) NOT in upcoming');
assert(upcoming.indexOf('NB 991v2 Made in UK') !== -1, 'NB 991v2 (20 mai) IS in upcoming');
assert(upcoming.indexOf('AJ4 Sept') !== -1,       'AJ4 Sept (futur lointain) IS in upcoming');
assert(upcoming.indexOf('TBD pair') !== -1,       'TBD pair toujours dans upcoming');

// ---- Test : dimanche 17 mai 2026 23h59 — toujours semaine en cours ----
var sunNight = new Date(2026, 4, 17, 23, 59, 0);
var wr2 = weekRange(sunNight);
assert(fmtFR(wr2.monday) === '11 mai', 'dim 17 23h59 : badge encore 11 mai');
assert(sunNight < wr2.nextMonday,      'dim 17 23h59 < lun 18 00h00 → badge ne bascule pas');

// ---- Test : lundi 18 mai 2026 00h01 — bascule semaine suivante ----
var monMorning = new Date(2026, 4, 18, 0, 1, 0);
var wr3 = weekRange(monMorning);
assert(fmtFR(wr3.monday) === '18 mai',  'lun 18 00h01 : nouvelle semaine commence');
assert(fmtFR(wr3.sunday) === '24 mai',  'lun 18 00h01 : fin de semaine = 24 mai');
assert(monMorning >= wr3.nextMonday === false, 'lun 18 < nextMonday(25) — pas encore bascule weekly_data override path');

// ---- Garde-fou : weekly_data.json livré en avance (week_start futur) ----
// Si on est encore le samedi 16 mai mais weekly_data.json contient déjà 18/05 → 24/05,
// le badge ne doit PAS être écrasé.
function shouldApplyWeeklyDataBadge(now, week_start, week_end) {
  var ws = week_start.split('/');
  var we = week_end.split('/');
  var ds = new Date(+ws[2], +ws[1]-1, +ws[0]); ds.setHours(0,0,0,0);
  var de = new Date(+we[2], +we[1]-1, +we[0]); de.setHours(23,59,59,999);
  return ds <= now && now <= de;
}
assert(!shouldApplyWeeklyDataBadge(now, '18/05/2026', '24/05/2026'),
       'samedi 16 mai : weekly_data 18→24 mai NE doit PAS écraser le badge');
assert( shouldApplyWeeklyDataBadge(monMorning, '18/05/2026', '24/05/2026'),
       'lundi 18 mai : weekly_data 18→24 mai PEUT écraser le badge');

// ---- Badge "Cette semaine" vs "À venir" — la logique isSoon doit s'appuyer
// sur la semaine en cours (lundi-dimanche locaux), pas sur un fenêtre de 7 jours
// glissants. Une paire du 20/05 vue depuis le 16/05 doit être "À venir".
function isSoonNew(dateStr, now) {
  if (!dateStr || dateStr === 'TBD') return false;
  var p = dateStr.split('-');
  if (p.length !== 3) return false;
  var d = new Date(+p[0], +p[1]-1, +p[2]);
  var day = now.getDay();
  var daysFromMon = day === 0 ? 6 : day - 1;
  var monday = new Date(now); monday.setDate(now.getDate() - daysFromMon); monday.setHours(0,0,0,0);
  var sunday = new Date(monday); sunday.setDate(monday.getDate() + 6); sunday.setHours(23,59,59,999);
  return d >= monday && d <= sunday;
}
// Bug constaté : AM90 du 20 mai badgée "Cette semaine" alors qu'on est le 16 mai.
assert( isSoonNew('2026-05-16', now), 'AJ3 Brazil (16 mai) → CETTE SEMAINE');
assert( isSoonNew('2026-05-17', now), 'Drop dim 17 mai → CETTE SEMAINE');
assert(!isSoonNew('2026-05-18', now), 'Drop lun 18 mai (semaine prochaine) → À VENIR (pas CETTE SEMAINE)');
assert(!isSoonNew('2026-05-20', now), 'AM90 Tiempo 20 mai → À VENIR (pas CETTE SEMAINE)');
assert( isSoonNew('2026-05-13', now), 'AM90 Hypervenom 13 mai (jour passé de la semaine) → CETTE SEMAINE');
assert(!isSoonNew('2026-09-25', now), 'Drop sept lointain → À VENIR');

// ---- Tri croissant pour "Drops de la semaine" ----
function sortAsc(arr) {
  return arr.slice().sort(function(a, b) {
    var da = a.date && a.date !== 'TBD' ? new Date(a.date) : new Date('9999-12-31');
    var db = b.date && b.date !== 'TBD' ? new Date(b.date) : new Date('9999-12-31');
    return da - db;
  });
}
var weeklyMix = [
  { title: 'Sun 17',  date: '2026-05-17' },
  { title: 'Mon 11',  date: '2026-05-11' },
  { title: 'Sat 16',  date: '2026-05-16' },
  { title: 'Tue 12',  date: '2026-05-12' },
];
var sortedTitles = sortAsc(weeklyMix).map(function(r){return r.title;});
assert(sortedTitles[0] === 'Mon 11' && sortedTitles[sortedTitles.length-1] === 'Sun 17',
       'Drops semaine triés croissant (du plus ancien au plus récent) — got ' + sortedTitles.join(' / '));

// ---- Filtrage cards sans image ----
function filterWithImage(arr) {
  return arr.filter(function(r){ return r.image_url && String(r.image_url).trim() !== ''; });
}
var mixedImg = [
  { title: 'A', image_url: 'https://example.com/a.jpg' },
  { title: 'B', image_url: '' },
  { title: 'C' },
  { title: 'D', image_url: '   ' },
  { title: 'E', image_url: 'https://example.com/e.jpg' },
];
var withImg = filterWithImage(mixedImg).map(function(r){return r.title;});
assert(withImg.length === 2 && withImg.join(',') === 'A,E',
       'Filtrage image utilisable : seules A et E gardées (got ' + withImg.join(',') + ')');

if (process.exitCode) {
  console.error('\n>>> Des tests ont échoué.');
} else {
  console.log('\n>>> Tous les tests passent.');
}
