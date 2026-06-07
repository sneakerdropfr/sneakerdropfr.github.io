function closeSearch() {
    var inp = document.getElementById('hero-search-input');
    if (inp) { inp.value = ''; }
    filterBySearch('');
    var cb = document.getElementById('hero-clear-btn');
    if (cb) cb.style.display = 'none';
  }

  function clearSearch() {
    var inp = document.getElementById('hero-search-input');
    var btn = document.getElementById('hero-clear-btn');
    if (inp) { inp.value = ''; inp.focus(); filterBySearch(''); }
    if (btn) btn.style.display = 'none';
  }
  // Dictionnaire d'alias pour la recherche
  var SEARCH_ALIASES = {
    'aj1': 'air jordan 1', 'aj2': 'air jordan 2', 'aj3': 'air jordan 3',
    'aj4': 'air jordan 4', 'aj5': 'air jordan 5', 'aj6': 'air jordan 6',
    'aj7': 'air jordan 7', 'aj8': 'air jordan 8', 'aj9': 'air jordan 9',
    'aj10': 'air jordan 10', 'aj11': 'air jordan 11', 'aj12': 'air jordan 12',
    'aj13': 'air jordan 13', 'aj14': 'air jordan 14', 'aj1 low': 'air jordan 1 low',
    'aj1 high': 'air jordan 1 high', 'aj1 mid': 'air jordan 1 mid',
    'am1': 'air max 1', 'am90': 'air max 90', 'am95': 'air max 95',
    'am97': 'air max 97', 'am270': 'air max 270',
    'nb550': 'new balance 550', 'nb574': 'new balance 574',
    'nb990': 'new balance 990', 'nb991': 'new balance 991',
    'nb992': 'new balance 992', 'nb993': 'new balance 993',
    'nb1906': 'new balance 1906', 'nb2002': 'new balance 2002',
    'ow': 'off-white', 'ts': 'travis scott', 'og': 'og',
    'dunk low': 'dunk low', 'dunk high': 'dunk high',
  };
  function expandAliases(q) {
    var result = q;
    // Remplacement exact (toute la query)
    if (SEARCH_ALIASES[q]) return SEARCH_ALIASES[q];
    // Remplacement partiel mot à mot
    var words = q.split(/\s+/);
    var expanded = words.map(function(w) { return SEARCH_ALIASES[w] || w; });
    return expanded.join(' ');
  }

  function filterBySearch(query) {
    var raw = (query || '').toLowerCase().trim();
    var q = expandAliases(raw);
    window._searchQuery = q;
    var overlay = document.getElementById('search-overlay');
    var overlayGrid = document.getElementById('search-overlay-grid');
    var overlayEmpty = document.getElementById('search-overlay-empty');
    var overlayTitle = document.getElementById('search-overlay-title');
    if (!q) { if (overlay) overlay.classList.remove('active'); if (overlayGrid) overlayGrid.innerHTML = ''; return; }
    if (overlay) { var hs = document.querySelector('.hero-search'); if (hs) { var r = hs.getBoundingClientRect(); overlay.style.top = (r.bottom) + 'px'; } overlay.classList.add('active'); }
    // Recherche dans tout le catalogue (actif + passé)
    var all = (window.allReleases || window._releases || []);
    // Recherche par mots-clés — chaque mot doit apparaître dans le titre, la marque, le SKU ou le colorway
    var words = q.split(/\s+/).filter(function(w){ return w.length > 0; });
    var results = all.filter(function(r) {
      var haystackMain = ((r.title || '') + ' ' + (r.brand || '') + ' ' + (r.sku || '') + ' ' + (r.colorway || '')).toLowerCase();
      return words.every(function(w){
        // Word boundary : le mot doit être suivi d'un espace, tiret, fin de chaîne ou chiffre de version (ex: 990v6)
        var escaped = w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
        var after = /\d$/.test(w) ? '(?=$|[\\s\\-\'"_/,]|v\\d)' : '(?=$|[\\s\\-\'"_/,])';
        var re = new RegExp('(?:^|[\\s\\-\'"_/(,])' + escaped + after, 'i');
        return re.test(haystackMain);
      });
    });
    // Trier : correspondance exacte en premier
    results.sort(function(a, b) {
      var ha = ((a.title || '') + ' ' + (a.brand || '')).toLowerCase();
      var hb = ((b.title || '') + ' ' + (b.brand || '')).toLowerCase();
      var ea = ha.indexOf(q) !== -1 ? 0 : 1;
      var eb = hb.indexOf(q) !== -1 ? 0 : 1;
      return ea - eb;
    });
    if (overlayTitle) overlayTitle.textContent = results.length + ' résultat' + (results.length > 1 ? 's' : '') + ' pour "' + query + '"';
    if (!results.length) {
      if (overlayGrid) overlayGrid.innerHTML = '';
      if (overlayEmpty) overlayEmpty.style.display = 'block';
      return;
    }
    if (overlayEmpty) overlayEmpty.style.display = 'none';
    if (overlayGrid) overlayGrid.innerHTML = results.map(function(r) {
      var imgHtml = r.image_url
        ? '<img src="' + r.image_url + '" alt="' + (r.title || '').replace(/"/g, '') + '" loading="lazy">'
        : '<div style="width:100%;aspect-ratio:1;background:#F5F5F5"></div>';
      var price = r.price ? r.price + ' €' : '';
      // Badge DISPO BSTN : uniquement pour paires à venir (date >= aujourd'hui ou pas encore sortie)
      var isFuture = r.date && r.date !== 'TBD' && r.date >= new Date().toISOString().slice(0,10);
      var badge = r.stock === 'rupture'
        ? '<span class="src__badge src__badge--rupture">Rupture</span>'
        : (r.buy_url && isFuture ? '<span class="src__badge src__badge--dispo">Dispo BSTN</span>' : '');
      var dateStr = '';
      if (r.date && r.date !== 'TBD') {
        var p = r.date.split('-');
        var d = new Date(parseInt(p[0]), parseInt(p[1]) - 1, parseInt(p[2]));
        dateStr = d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
      }
      var link = r.id ? 'sorties/' + r.id + '.html' : (r.buy_url || r.wtc_url || '#');
      return '<a href="' + link + '" class="src">'
        + imgHtml + '<div class="src__body"><div class="src__title">' + escapeHtml(r.title) + '</div>'
        + '<div class="src__meta"><span>' + dateStr + '</span><span class="src__price">' + price + '</span></div>'
        + (badge ? badge : '') + '</div></a>';
    }).join('');
  }
  document.addEventListener('click', function(e) {
    var heroSearch = document.querySelector('.hero-search');
    var overlay = document.getElementById('search-overlay');
    if (e.target.closest && e.target.closest('a')) return;
    if (heroSearch && overlay && !heroSearch.contains(e.target) && !overlay.contains(e.target)) {
      overlay.classList.remove('active');
      window._searchQuery = '';
    }
  });