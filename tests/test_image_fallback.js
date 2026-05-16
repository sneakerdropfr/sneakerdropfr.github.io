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
  // Le sweep doit aussi être présent pour rattraper les images dont l'onerror
  // ne se déclenche pas (200 OK mais naturalWidth=0).
  assert(/function sdfSweepBrokenImages/.test(h),
         p + ' définit sdfSweepBrokenImages (naturalWidth=0 sweep)');
  assert(/window\.sdfSweepBrokenImages\s*=\s*sdfSweepBrokenImages/.test(h),
         p + ' expose window.sdfSweepBrokenImages');
  assert(/DOMContentLoaded[^]*sdfSweepBrokenImages/.test(h),
         p + ' déclenche sdfSweepBrokenImages au DOMContentLoaded');
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
  // Vague 2 (commit après 8fb5a39) : images encore cassées détectées en live.
  /sneakerfiles\.com\/wp-content\/uploads\/2025\/07\/nike-air-griffey-max-1-freshwater-2026-DD8558-100-1024x725\.jpg/,
  /cdn\.lesitedelasneaker\.com\/wp-content\/images\/2026\/02\/air-jordan-3-brazil-iv4871-400-2-1100x1100\.jpg/,
  /statics\.whentocop\.fr\/media\/cU0tOTO1Flnu\/tmpair-jordan-1-low-og-black-red-iw6276-001-small-500x500\.webp/,
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

// -- 8. Sweep dynamique : une image avec naturalWidth=0 doit masquer sa card parent.
//        On simule un DOM minimal et on extrait le code de sweep d'index.html.
(function testSweepHidesBrokenCard() {
  var idx = read('index.html');
  // Extraire le bloc <script> contenant sdfHideBrokenCard…
  var m = idx.match(/<script>\s*function escapeHtml[\s\S]*?<\/script>/);
  assert(!!m, 'extraction du bloc <script> sweep depuis index.html');
  if (!m) return;
  var src = m[0].replace(/^<script>/, '').replace(/<\/script>$/, '');

  // DOM mock minimal : ChildNode + querySelectorAll + closest + matches + addEventListener.
  function makeEl(tag, className) {
    var el = {
      tagName: tag.toUpperCase(),
      nodeType: 1,
      className: className || '',
      children: [],
      parentNode: null,
      style: {},
      attrs: {},
      complete: false,
      naturalWidth: 0,
      _listeners: {},
      setAttribute: function(k, v) { this.attrs[k] = v; },
      getAttribute: function(k) { return this.attrs[k] != null ? String(this.attrs[k]) : null; },
      removeAttribute: function(k) { delete this.attrs[k]; },
      addEventListener: function(ev, fn) { (this._listeners[ev] = this._listeners[ev] || []).push(fn); },
      dispatch: function(ev) { (this._listeners[ev] || []).forEach(function(f){ f({ target: el }); }); },
      appendChild: function(c) { c.parentNode = this; this.children.push(c); return c; },
      removeChild: function(c) {
        var i = this.children.indexOf(c);
        if (i !== -1) { this.children.splice(i, 1); c.parentNode = null; }
        return c;
      },
      matches: function(sel) {
        var parts = sel.split(',').map(function(s){return s.trim();});
        for (var i = 0; i < parts.length; i++) {
          var p = parts[i];
          if (p.charAt(0) === '.') {
            if ((' '+this.className+' ').indexOf(' '+p.slice(1)+' ') !== -1) return true;
          } else if (p === this.tagName.toLowerCase()) {
            return true;
          }
        }
        return false;
      },
      closest: function(sel) {
        var n = this;
        while (n) { if (n.matches && n.matches(sel)) return n; n = n.parentNode; }
        return null;
      },
      querySelectorAll: function(sel) {
        var out = [];
        function walk(node) {
          for (var i = 0; i < node.children.length; i++) {
            var c = node.children[i];
            if (sel === 'img') { if (c.tagName === 'IMG') out.push(c); }
            else if (c.matches && c.matches(sel)) out.push(c);
            walk(c);
          }
        }
        walk(this);
        return out;
      }
    };
    return el;
  }
  var doc = makeEl('html');
  var body = makeEl('body');
  doc.body = body;
  body.parentNode = doc;
  doc.appendChild(body);
  // Card .drop-card > a.drop-card__img-wrap > img (image cassée, naturalWidth=0)
  var card = makeEl('article', 'drop-card');
  var wrap = makeEl('a', 'drop-card__img-wrap');
  var img  = makeEl('img', 'drop-card__img');
  img.complete = true; img.naturalWidth = 0; img.src = 'http://broken/case1.jpg';
  body.appendChild(card); card.appendChild(wrap); wrap.appendChild(img);
  // Stubs globaux pour le bout de code extrait
  doc.addEventListener = function(){};
  doc.querySelectorAll = body.querySelectorAll.bind(body);
  var win = {
    MutationObserver: function() { this.observe = function(){}; },
    sdfHideBrokenCard: null,
    sdfSweepBrokenImages: null
  };
  // Évalue le bloc dans un scope contrôlé
  try {
    var run = new Function('window', 'document', src + '\nreturn { hide: sdfHideBrokenCard, sweep: sdfSweepBrokenImages, isBroken: sdfIsBrokenImg };');
    var api = run(win, doc);
    api.sweep(body);
    assert(card.style.display === 'none',
           'sweep masque la .drop-card parent quand naturalWidth=0 (display:none)');
    assert(card.attrs['data-broken-image'] === '1',
           'sweep marque la card avec data-broken-image=1');
    // Critère d'acceptation Playwright : l'<img> elle-même doit être masquée
    // (display:none) ET/OU retirée du DOM. On vérifie les deux côtés.
    var imgGone = wrap.children.indexOf(img) === -1;
    var imgHidden = img.style.display === 'none';
    assert(imgGone || imgHidden,
           "sweep masque l'<img> elle-même (display:none) ou la retire du DOM");
    assert(img.attrs['data-sdf-broken'] === '1',
           "sweep marque l'img avec data-sdf-broken=1");
  } catch (e) {
    assert(false, 'sweep exécutable dans un DOM mock : ' + e.message);
  }

  // Cas 2 : image qui charge tardivement (load après sweep) avec naturalWidth=0.
  var card2 = makeEl('article', 'drop-card');
  var wrap2 = makeEl('div', 'drop-card__img-wrap');
  var img2  = makeEl('img', 'drop-card__img');
  img2.complete = false; img2.naturalWidth = 0; img2.src = 'http://broken/2';
  body.appendChild(card2); card2.appendChild(wrap2); wrap2.appendChild(img2);
  try {
    var run2 = new Function('window', 'document', src + '\nreturn { sweep: sdfSweepBrokenImages };');
    var api2 = run2(win, doc);
    api2.sweep(body);
    // L'image finit par charger mais avec naturalWidth=0 → load event doit cacher.
    img2.complete = true; img2.naturalWidth = 0;
    img2.dispatch('load');
    assert(card2.style.display === 'none',
           'sweep masque la card quand load se déclenche tardivement avec naturalWidth=0');
    var img2Gone = wrap2.children.indexOf(img2) === -1;
    var img2Hidden = img2.style.display === 'none';
    assert(img2Gone || img2Hidden,
           "sweep masque l'<img> tardive elle-même ou la retire du DOM");
  } catch (e) {
    assert(false, 'sweep gère le load tardif : ' + e.message);
  }

  // Cas 3 : critère Playwright — Array.from(images).filter(visible && broken) doit être vide.
  // On simule plusieurs cards sur la page, certaines OK, certaines cassées.
  // Après sweep, aucune img restante visible (style.display !== 'none') ne doit être broken.
  var bigBody = makeEl('body');
  var doc3 = makeEl('html'); doc3.body = bigBody; bigBody.parentNode = doc3;
  doc3.addEventListener = function(){}; doc3.querySelectorAll = bigBody.querySelectorAll.bind(bigBody);
  function addCard(broken, srcUrl) {
    var c = makeEl('article', 'drop-card');
    var w = makeEl('a', 'drop-card__img-wrap');
    var i = makeEl('img', 'drop-card__img');
    i.complete = true; i.naturalWidth = broken ? 0 : 800; i.src = srcUrl;
    bigBody.appendChild(c); c.appendChild(w); w.appendChild(i);
    return { card: c, wrap: w, img: i };
  }
  var a = addCard(true,  'http://x/broken-griffey.jpg');
  var b = addCard(false, 'http://x/ok-nike.jpg');
  var c3 = addCard(true,  'http://x/broken-aj3.png');
  var d = addCard(true,  'http://x/broken-aj1.png');
  var e = addCard(false, 'http://x/ok-adidas.jpg');
  var run3 = new Function('window', 'document', src + '\nreturn { sweep: sdfSweepBrokenImages };');
  run3({ MutationObserver: function(){ this.observe = function(){}; } }, doc3).sweep(bigBody);
  // Collecter toutes les <img> restantes dans le DOM ET visibles.
  function collectImgs(node, out) {
    for (var i = 0; i < node.children.length; i++) {
      var ch = node.children[i];
      if (ch.tagName === 'IMG') out.push(ch);
      collectImgs(ch, out);
    }
  }
  var remaining = []; collectImgs(bigBody, remaining);
  var visibleBroken = remaining.filter(function(im) {
    var hidden = im.style.display === 'none' || im.style.visibility === 'hidden';
    var brokenByPw = !im.complete || im.naturalWidth === 0; // critère Playwright
    return !hidden && brokenByPw;
  });
  assert(visibleBroken.length === 0,
         'critère Playwright : aucune <img> visible avec naturalWidth=0 après sweep (got ' + visibleBroken.length + ')');
  // Les images OK restent intactes
  assert(b.img.style.display !== 'none' && e.img.style.display !== 'none',
         'sweep ne touche pas les images OK (naturalWidth>0)');
  assert(b.card.style.display !== 'none' && e.card.style.display !== 'none',
         'sweep ne masque pas les cards OK');
})();

if (process.exitCode) {
  console.error('\n>>> Des tests ont échoué.');
} else {
  console.log('\n>>> Tous les tests image-fallback passent.');
}
