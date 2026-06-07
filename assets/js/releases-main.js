(function(){
    var RELEASES_URL='https://raw.githubusercontent.com/sneakerdropfr/sneakerdropfr.github.io/main/releases.json?t='+Date.now();
    var grid=document.getElementById('releases-grid-week');
    var gridUpcoming=document.getElementById('releases-grid-upcoming');
    var weeklyDropsGrid=document.getElementById('weekly-drops-grid');
    var weeklyDropsBadge=document.getElementById('weekly-drops-badge');
    var weeklyDropsEmpty=document.getElementById('weekly-drops-empty');
    var empty=document.getElementById('releases-empty');
    var loading=document.getElementById('releases-loading');
    var topPickCard=document.getElementById('top-pick-card');
    var MAX_CARDS=50;
    var allReleases=[]; window._releases=[]; window._render=null;
    var activeFilter='all';
    var BRAND_MAP={'jordan':['jordan brand','jordan'],'nike':['nike'],'adidas':['adidas'],'new balance':['new balance']};

    function isReleased(dateStr) {
      if (!dateStr || dateStr === 'TBD') return false;
      var p = dateStr.split('-');
      if (p.length !== 3) return false;
      var releaseDate = new Date(parseInt(p[0]), parseInt(p[1])-1, parseInt(p[2]));
      var tomorrow = new Date(); tomorrow.setHours(0,0,0,0); tomorrow.setDate(tomorrow.getDate() + 1);
      // Sorti = date strictement avant aujourd'hui (hier ou avant)
      return releaseDate < new Date(new Date().setHours(0,0,0,0));
    }
    function isToday(dateStr) {
      if (!dateStr || dateStr === 'TBD') return false;
      var p = dateStr.split('-');
      if (p.length !== 3) return false;
      var d = new Date(parseInt(p[0]), parseInt(p[1])-1, parseInt(p[2]));
      var today = new Date(); today.setHours(0,0,0,0);
      return d.getTime() === today.getTime();
    }
    function isFutureOrToday(dateStr) {
      if (!dateStr || dateStr === 'TBD') return true;
      return new Date(dateStr + 'T23:59:59') >= new Date();
    }
    function isSoon(dateStr) {
      if (!dateStr || dateStr === 'TBD') return false;
      var p = dateStr.split('-');
      if (p.length !== 3) return false;
      var dropDate = new Date(parseInt(p[0]), parseInt(p[1])-1, parseInt(p[2]));
      var today = new Date(); today.setHours(0,0,0,0);
      var diff = (dropDate - today) / (1000*60*60*24);
      return diff >= 0 && diff <= 7;
    }
    function getScore(r) {
      var score = 0;
      if (r.featured) score += 1000;
      var clicks = {};
      try { clicks = JSON.parse(localStorage.getItem('sdf_clicks') || '{}'); } catch(e) {}
      if (clicks[r.title]) score += clicks[r.title] * 0.5;
      if (r.date && r.date !== 'TBD') {
        var diff = (new Date(r.date + 'T12:00:00') - new Date()) / (1000*60*60*24);
        if (diff >= 0 && diff <= 3) score += 4;
        else if (diff > 0 && diff <= 7) score += 2;
      }
      var brand = (r.brand || '').toLowerCase();
      var title = (r.title || '').toLowerCase();
      if (brand.indexOf('jordan') !== -1) score += 40;
      else if (brand.indexOf('nike') !== -1) score += 20;
      else if (brand.indexOf('adidas') !== -1) score += 15;
      else if (brand.indexOf('new balance') !== -1) score += 15;
      var collabs = ['travis scott','nigel sylvester','off-white','patta','sacai','nocta','bad bunny','union','fragment','clot'];
      for (var i=0; i<collabs.length; i++) { if (title.indexOf(collabs[i]) !== -1) { score += 50; break; } }
      var premium = ['jordan 4','jordan 1','jordan 11','jordan 3','jordan 12','dunk','990','991','2002'];
      for (var j=0; j<premium.length; j++) { if (title.indexOf(premium[j]) !== -1) { score += 25; break; } }
      if (r.resell) score += 30;
      if (r.buy_url) score += 5;
      return score;
    }
    function matchBrand(r, filter) {
      if (filter === 'all') return true;
      var b = (r.brand || '').toLowerCase();
      var keys = BRAND_MAP[filter.toLowerCase()] || [filter.toLowerCase()];
      return keys.some(function(k) { return b.indexOf(k) !== -1; });
    }
    function formatPrice(p) {
      if (!p && p !== 0) return '';
      var s = String(p).trim().replace(/€/g, '').replace(/EUR/gi, '').trim();
      if (!s) return '';
      return s + ' €';
    }
    window.formatPrice = formatPrice;
    function formatDate(str) {
      if (!str || str === 'TBD') return 'Date à confirmer';
      try {
        var parts = str.split('-');
        if (parts.length === 3) {
          var d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
          return d.toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'long' });
        }
        return str;
      } catch(e) { return str; }
    }
    function sortByDate(arr) {
      return arr.slice().sort(function(a, b) {
        var da = a.date && a.date !== 'TBD' ? new Date(a.date) : new Date('9999-12-31');
        var db = b.date && b.date !== 'TBD' ? new Date(b.date) : new Date('9999-12-31');
        return da - db;
      });
    }
    function sortByScore(arr) {
      return arr.slice().sort(function(a, b) { return getScore(b) - getScore(a); });
    }
    function safeTitle(t) { return (t || '').replace(/'/g, "\\'").replace(/"/g, '&quot;'); }
    function escapeHtml(t) { return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }


    // Retailers connus en marché secondaire (resell)
    var RESELL_RETAILERS = ['stockx','goat','klekt','limited resell'];
    // Retailers Nike/Jordan officiels
    var NIKE_RETAILERS = ['nike','nike snkrs'];
    // BSTN
    function isRetailerBSTN(name){ return name.toLowerCase()==='bstn'; }
    function isRetailerResell(name){ return RESELL_RETAILERS.indexOf(name.toLowerCase())!==-1; }
    function isRetailerNike(name){ return NIKE_RETAILERS.indexOf(name.toLowerCase())!==-1; }

    function makeRetailersRow(r, isBig) {
      var retailers = r.retailers;
      // Si pas de retailers → fallback makeBtn
      if (!retailers || !retailers.length) return makeBtn(r, isBig);

      // Séparer officiels et resell
      var official = retailers.filter(function(rt){ return !isRetailerResell(rt.name); });
      var resell = retailers.filter(function(rt){ return isRetailerResell(rt.name); });

      var html = '';

      // Officiels — max 3 sur la card, bouton "Voir tout" si plus
      if (official.length) {
        var officialShown = official.slice(0, 3);
        var hasMore = official.length > 3;
        var sortiePage = r.id ? 'sorties/' + r.id + '.html' : null;
        html += '<div class="retailers-label">Acheter</div><div class="retailers-row">';
        officialShown.forEach(function(rt) {
          var cls = isRetailerBSTN(rt.name) ? 'btn-retailer btn-retailer--bstn'
                  : isRetailerNike(rt.name) ? 'btn-retailer btn-retailer--nike'
                  : 'btn-retailer btn-retailer--official';
          var icon = isRetailerBSTN(rt.name) ? '🛒 '
                   : isRetailerNike(rt.name) ? '✓ '
                   : '';
          var priceStr = rt.price ? ' <span style="opacity:.6;font-size:.65rem">' + rt.price + '</span>' : '';
          html += '<a href="' + rt.url + '" target="_blank" rel="noopener" class="' + cls + '" onclick="trackBSTN(\'' + safeTitle(rt.name + ' - ' + (r.title||'')) + '\')">'
                + icon + escapeHtml(rt.name) + priceStr + '</a>';
        });
        if (hasMore && sortiePage) {
          html += '<a href="' + sortiePage + '" class="btn-retailer btn-retailer--more">+' + (official.length - 3) + ' voir tout →</a>';
        }
        html += '</div>';
      }

      // Resell masqué (affiliation)

      return html || makeBtn(r, isBig);
    }
    function makeBtn(r, isBig) {
      var released = isReleased(r.date);
      var hasAff = r.buy_url && r.buy_url.indexOf('awin') !== -1;
      if (r.stock === 'rupture') {
        var clsR = isBig ? 'btn-cop-big btn-cop-big--sold' : 'btn-cop btn-cop--sold';
        return '<span class="' + clsR + '">Rupture de stock</span>';
      }
      if (r.buy_url && (released || hasAff)) {
        var label = released ? '🔥 Acheter Avant Rupture' : '🛒 Acheter sur BSTN';
        var cls = isBig ? 'btn-cop-big' : 'btn-cop';
        return '<a href="' + r.buy_url + '" target="_blank" rel="noopener" class="' + cls + '" onclick="trackBSTN(\'' + safeTitle(r.title) + '\')">' + label + '</a>';
      } else {
        var wtcLink = r.wtc_url || ('https://www.whentocop.fr/search?q=' + encodeURIComponent(r.title || ''));
        var cls2 = isBig ? 'btn-cop-big btn-cop-big--alert' : 'btn-cop btn-cop--alert';
        return '<a href="' + wtcLink + '" target="_blank" rel="noopener" class="' + cls2 + '">Voir sur WhenToCop</a>';
      }
    }

    function renderTopPick(r) {
      if (!r || !topPickCard) return;
      var released = isReleased(r.date);
      var img = r.image_url ? '<img src="' + r.image_url + '" alt="' + r.title + '" class="top-pick__img" loading="lazy" onerror="this.style.display=\'none\'">' : '';
      var alertDiv = released
        ? '<div class="top-pick__alert">⚠️ Déjà en rupture sur plusieurs sites — encore dispo ici</div>'
        : '<div class="top-pick__alert top-pick__alert--upcoming">📅 Drop le ' + formatDate(r.date) + ' — Active ton alerte maintenant</div>';
      topPickCard.innerHTML =
        '<div class="top-pick__tag">🔥 Top Pick de la semaine</div>' +
        '<div class="top-pick__img-wrap">' + img + '</div>' +
        '<div class="top-pick__body">' +
          '<span class="top-pick__brand">' + (r.brand || '') + '</span>' +
          '<h2 class="top-pick__title">' + escapeHtml(r.title) + '</h2>' +
          '<div class="top-pick__price">' + formatPrice(r.price) + '</div>' +

          '<div class="top-pick__date">📅 ' + formatDate(r.date) + '</div>' +
          alertDiv +
          makeRetailersRow(r, true) +
        '</div>';
    }

    // IDs dont l'image pointe vers la gauche -> à retourner
    var FLIP_IDS = []; // toutes les images sont retournées par défaut via CSS
    var NO_FLIP_IDS = ['air-jordan-3-brazil-releases-may-2026','air-jordan-3-brazil'];
    function renderCard(r, index) {
      var released = isReleased(r.date);
      var skuMatch = (r.id || '').match(/([a-z]{1,3}[0-9]{4,6}-[0-9]{3,4})(?:[^-]|$)/i);
      var cardSku = skuMatch ? skuMatch[1] : '';
      var noFlip = NO_FLIP_IDS.indexOf(r.id || '') !== -1;
      var imgStyle = noFlip ? ' style="transform:scaleX(1)"' : '';
      var img = r.image_url
        ? '<img src="' + r.image_url + '" alt="' + r.title + '" class="drop-card__img" loading="lazy"' + imgStyle + ' onerror="this.parentNode.innerHTML='<div class=drop-card__img-placeholder><svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 80 60' width='80' height='60'><rect width='80' height='60' fill='#F5F5F5'/><path d='M15 40 Q25 20 40 22 Q55 24 65 38 L65 42 Q55 48 40 46 Q25 44 15 42 Z' fill='#E0E0E0'/><path d='M30 22 L35 16 Q40 12 45 16 L50 22' fill='none' stroke='#CCC' stroke-width='2'/></svg></div>'">'
        : '<div class="drop-card__img-placeholder"><svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 80 60' width='80' height='60'><rect width='80' height='60' fill='#F5F5F5'/><path d='M15 40 Q25 20 40 22 Q55 24 65 38 L65 42 Q55 48 40 46 Q25 44 15 42 Z' fill='#E0E0E0'/><path d='M30 22 L35 16 Q40 12 45 16 L50 22' fill='none' stroke='#CCC' stroke-width='2'/></svg></div>';
      var isDropToday = isToday(r.date);
      var titleLC = (r.title || '').toLowerCase();
      var isHypeCollab = ['travis scott','bad bunny','patta','off-white','sacai','fragment','union','kaws','stussy','corteiz'].some(function(k){ return titleLC.indexOf(k) !== -1; });
      var officialRets = (r.retailers || []).filter(function(rt){ return !rt.resell && !rt.raffle; });
      var isLimitedDrop = officialRets.length > 0 && officialRets.length <= 3;
      var badgeTop = released
        ? '<div class="drop-card__badge-top badge-week">🔥 Dispo</div>'
        : (isDropToday
            ? '<div class="drop-card__badge-top badge-hot" style="background:#FF2D2D">🔥 AUJOURD\'HUI</div>'
            : (isSoon(r.date)
                ? '<div class="drop-card__badge-top badge-hot">⏰ Cette semaine</div>'
                : '<div class="drop-card__badge-top badge-upcoming">📅 À venir</div>'));
      if (isHypeCollab && !released) badgeTop = '<div class="drop-card__badge-top badge-hype">⚡ Très attendu</div>';
      else if (isLimitedDrop && !released && !isDropToday) badgeTop += '<div class="drop-card__badge-top" style="position:absolute;top:2.2rem;left:.65rem;background:#FF3B30;color:#fff;font-family:var(--font-cond);font-size:.6rem;font-weight:900;letter-spacing:.06em;text-transform:uppercase;padding:.2rem .5rem;border-radius:3px;">🚨 Stock limité</div>';
      var urgency = released ? '⚠️ Stock limité' : (!r.date || r.date === 'TBD' ? 'DROP À VENIR' : '');
      var urgencyClass = released ? 'drop-card__stock' : 'drop-card__stock drop-card__stock--upcoming';
      var hasLink = (r.retailers && r.retailers.length) || r.buy_url || r.wtc_url;
      var articleUrl = (r.id && hasLink) ? 'sorties/' + r.id + '.html' : null;
      var imgWrap = articleUrl
        ? '<a href="' + articleUrl + '" class="drop-card__img-wrap" style="display:block">' + badgeTop + img + '</a>'
        : '<div class="drop-card__img-wrap">' + badgeTop + img + '</div>';
      var titleWrap = articleUrl
        ? '<a href="' + articleUrl + '" style="color:inherit"><h3 class="drop-card__title">' + escapeHtml(r.title) + '</h3></a>'
        : '<h3 class="drop-card__title">' + escapeHtml(r.title) + '</h3>';
      // Badge hype_score
      var hypeScoreHtml = '';
      if (r.hype_score && r.hype_score >= 40) {
        var hs = r.hype_score;
        var hsCls = hs >= 80 ? 'hype-score--hot' : hs >= 60 ? 'hype-score--hype' : 'hype-score--mid';
        var hsIcon = hs >= 80 ? '🔥' : hs >= 60 ? '⚡' : '●';
        hypeScoreHtml = '<div class="hype-score ' + hsCls + '">' + hsIcon + ' ' + hs + '/100</div>';
      }
      // Difficulté d'achat dérivée du hype_score
      var difficultyHtml = '';
      if (r.hype_score) {
        var hs2 = r.hype_score;
        if (hs2 >= 70) difficultyHtml = '<div class="difficulty difficulty--hard">🎯 Difficile</div>';
        else if (hs2 >= 40) difficultyHtml = '<div class="difficulty difficulty--medium">🎯 Moyen</div>';
        else difficultyHtml = '<div class="difficulty difficulty--easy">🎯 Facile</div>';
      }
      // Countdown : afficher si date connue, pas encore sortie, dans moins de 72h
      var countdownHtml = '';
      if (!released && r.date && r.date !== 'TBD') {
        var dropTs = (function() {
          var p = r.date.split('-');
          return p.length === 3 ? new Date(+p[0], +p[1]-1, +p[2]).getTime() : 0;
        })();
        var diffMs = dropTs - Date.now();
        if (dropTs && diffMs > 0 && diffMs < 72 * 3600 * 1000) {
          countdownHtml = '<div class="drop-card__countdown" data-target="' + dropTs + '">⏱ </div>';
        }
      }
      return '<article class="drop-card"' + (cardSku ? ' data-sku="' + cardSku + '"' : '') + ' data-title="' + safeTitle(r.title) + '">' + imgWrap +
        '<div class="drop-card__body">' +
          '<span class="drop-card__brand">' + (r.brand || '') + '</span>' +
          titleWrap +
          hypeScoreHtml +
          difficultyHtml +
          '<div class="drop-card__meta">' +
            '<span class="drop-card__date">📅 ' + formatDate(r.date) + '</span>' +
            '<span class="drop-card__price">' + formatPrice(r.price) + '</span>' +
          '</div>' +
          countdownHtml +
          (urgency ? '<div class="' + urgencyClass + '">' + urgency + '</div>' : '') +
          '<div class="drop-card__cta">' + makeRetailersRow(r, false) + '</div>' +
        '</div>' +
      '</article>';
    }

    function render() {
      var _now = new Date();
      var _day = _now.getDay();
      var _daysFromMon = _day === 0 ? 6 : _day - 1;
      var _monday = new Date(_now); _monday.setDate(_now.getDate() - _daysFromMon); _monday.setHours(0,0,0,0);
      var _sunday = new Date(_monday); _sunday.setDate(_monday.getDate() + 6); _sunday.setHours(23,59,59,999);
      // Semaine suivante (bascule lundi 00:00 local)
      var _nextMonday = new Date(_monday); _nextMonday.setDate(_monday.getDate() + 7);
      var _nextSunday = new Date(_nextMonday); _nextSunday.setDate(_nextMonday.getDate() + 6); _nextSunday.setHours(23,59,59,999);
      if (weeklyDropsBadge) {
        weeklyDropsBadge.textContent = _monday.toLocaleDateString('fr-FR',{day:'numeric',month:'short'}) + ' \u2192 ' + _sunday.toLocaleDateString('fr-FR',{day:'numeric',month:'short'});
      }
      function parseDateLocal(str) {
        var p = str.split('-');
        return p.length === 3 ? new Date(parseInt(p[0]), parseInt(p[1])-1, parseInt(p[2])) : null;
      }
      var notReleased = allReleases.filter(function(r) {
        if (!r.date || r.date === 'TBD') return true;
        var d = parseDateLocal(r.date);
        if (!d) return true;
        var todayMidnight = new Date(); todayMidnight.setHours(0,0,0,0);
        return d >= todayMidnight;
      });
      var filtered = notReleased.filter(function(r) { return matchBrand(r, activeFilter); });
      if (window._searchQuery) {
        // Recherche dans tout le catalogue (à venir + passés)
        var allFiltered = (window.allReleases || []).filter(function(r) {
          return ((r.title||'').toLowerCase().indexOf(window._searchQuery) !== -1
              || (r.brand||'').toLowerCase().indexOf(window._searchQuery) !== -1)
              && matchBrand(r, activeFilter);
        });
        filtered = allFiltered;
      }
      var sorted = sortByDate(filtered).slice(0, MAX_CARDS);
      if (!sorted.length) {
        if (grid) grid.style.display = 'none';
        if (gridUpcoming) gridUpcoming.style.display = 'none';
        document.getElementById('this-week-header').style.display = 'none';
        document.getElementById('upcoming-header').style.display = 'none';
        if (weeklyDropsGrid) { weeklyDropsGrid.style.display = 'none'; weeklyDropsGrid.innerHTML = ''; }
        if (weeklyDropsEmpty) weeklyDropsEmpty.style.display = 'block';
        if (empty) empty.style.display = window._searchQuery ? 'none' : 'block';
        return;
      }
      if (empty) empty.style.display = 'none';
      // thisWeek : toutes les paires semaine ISO en cours (lundi-dimanche inclus jours passes)
      var thisWeek = allReleases.filter(function(r) {
        if (!r.date || r.date === 'TBD') return false;
        var d = parseDateLocal(r.date);
        return d && d >= _monday && d <= _sunday;
      });
      var laterOn = sorted.filter(function(r) {
        if (!r.date || r.date === 'TBD') return true;
        var d = parseDateLocal(r.date);
        return !d || d > _sunday;
      });
      // Weekly drops section — chargé depuis weekly_data.json
      (function loadWeeklyData() {
        var WEEKLY_BRAND_MAP = {'jordan':['jordan brand','jordan'],'nike':['nike'],'adidas':['adidas'],'new balance':['new balance']};
        var weeklyActiveFilter = 'all';
        var allWdrops = [];

        function matchWeeklyBrand(r, filter) {
          if (filter === 'all') return true;
          var b = (r.brand || '').toLowerCase();
          var keys = WEEKLY_BRAND_MAP[filter.toLowerCase()] || [filter.toLowerCase()];
          return keys.some(function(k) { return b.indexOf(k) !== -1; });
        }

        function renderWeeklyDrops() {
          if (!weeklyDropsGrid) return;
          var filtered = sortByDate(allWdrops.filter(function(r) { return matchWeeklyBrand(r, weeklyActiveFilter); }));
          if (filtered.length) {
            weeklyDropsGrid.style.display = 'grid';
            weeklyDropsGrid.innerHTML = filtered.map(function(r, i) { return renderCard(r, i); }).join('');
            if (weeklyDropsEmpty) weeklyDropsEmpty.style.display = 'none';
          } else {
            weeklyDropsGrid.style.display = 'none';
            if (weeklyDropsEmpty) weeklyDropsEmpty.style.display = 'block';
          }
        }

        // Filtres marque drops de la semaine
        document.querySelectorAll('#weekly-filters .filter-btn').forEach(function(btn) {
          btn.addEventListener('click', function() {
            document.querySelectorAll('#weekly-filters .filter-btn').forEach(function(b) { b.classList.remove('active'); });
            btn.classList.add('active');
            weeklyActiveFilter = btn.getAttribute('data-weekly');
            renderWeeklyDrops();
          });
        });

        // Avant lundi 00:00 local : afficher la semaine en cours depuis releases.json
        if (_now < _nextMonday) {
          allWdrops = thisWeek;
          renderWeeklyDrops();
          return;
        }
        fetch('https://raw.githubusercontent.com/sneakerdropfr/sneakerdropfr.github.io/main/weekly_data.json?t=' + Date.now())
          .then(function(res) { return res.json(); })
          .then(function(wd) {
            // Vérifier que weekly_data.json correspond bien à la semaine en cours ou future
            // Si week_end est dans le passé → fallback releases.json
            try {
              var we = (wd.week_end||'').split('/');
              if (we.length===3) {
                var weDate = new Date(+we[2],+we[1]-1,+we[0]);
                weDate.setHours(23,59,59,999);
                if (weDate < _now) {
                  // weekly_data.json périmé → fallback sur releases.json cette semaine
                  allWdrops = thisWeek;
                  renderWeeklyDrops();
                  return;
                }
              }
            } catch(e) {}
            // Index releases.json par titre normalisé pour enrichissement
            function normTitle(t) { return (t||'').toLowerCase().trim().replace(/[\u2018\u2019\u201c\u201d\u00ab\u00bb"]/g,"'"); }
            var relIdx = {};
            (allReleases || []).forEach(function(rel) {
              var key = normTitle(rel.title);
              if (key) relIdx[key] = rel;
            });

            allWdrops = (wd.releases || []).map(function(r) {
              var dparts = (r.date||'').split('/');
              var isoDate = dparts.length===3 ? (dparts[2]+'-'+dparts[1]+'-'+dparts[0]) : r.date;
              var wTitle = r.name || r.title || '';
              // Chercher la paire correspondante dans releases.json (par titre exact ou partiel)
              var rel = relIdx[normTitle(wTitle)];
              if (!rel) {
                // Fallback : chercher si le titre releases contient le titre weekly ou vice-versa
                var wNorm = normTitle(wTitle);
                Object.keys(relIdx).forEach(function(k) {
                  if (!rel && (k.indexOf(wNorm) !== -1 || wNorm.indexOf(k) !== -1)) {
                    rel = relIdx[k];
                  }
                });
              }
              return {
                title: wTitle,
                brand: r.brand || (rel && rel.brand) || '',
                date: isoDate,
                price: r.price || (rel && rel.price) || '',
                image_url: r.image || r.image_url || (rel && rel.image_url) || '',
                wtc_url: r.wtc_url || r.link || (rel && rel.wtc_url) || '',
                buy_url: r.buy_url || r.buy_link || (rel && rel.buy_url) || '',
                id: r.id || (rel && rel.id) || '',
                resell: r.resell || (rel && rel.resell) || '',
                stock: r.stock || (rel && rel.stock) || '',
                retailers: (rel && rel.retailers) || r.retailers || null
              };
            });
            // Badge : si on est lundi ou après, afficher la semaine de weekly_data.json
            if (weeklyDropsBadge && _now >= _nextMonday) {
              try {
                var ws = (wd.week_start||'').split('/');
                var we = (wd.week_end||'').split('/');
                var ds = ws.length===3 ? new Date(+ws[2],+ws[1]-1,+ws[0]) : null;
                var de = we.length===3 ? new Date(+we[2],+we[1]-1,+we[0]) : null;
                if (ds && de) weeklyDropsBadge.textContent = ds.toLocaleDateString('fr-FR',{day:'numeric',month:'short'}) + ' → ' + de.toLocaleDateString('fr-FR',{day:'numeric',month:'short'});
              } catch(e){}
            }
            renderWeeklyDrops();
          })
          .catch(function() {
            // Fallback releases.json
            allWdrops = thisWeek;
            renderWeeklyDrops();
          });
      })();
      document.getElementById('this-week-header').style.display = 'none';
      if (grid) grid.style.display = 'none';
      if (laterOn.length) {
        document.getElementById('upcoming-header').style.display = 'block';
        gridUpcoming.style.display = 'grid';
        gridUpcoming.innerHTML = laterOn.map(function(r, i) { return renderCard(r, i); }).join('');
      } else {
        document.getElementById('upcoming-header').style.display = 'none';
        if (gridUpcoming) gridUpcoming.style.display = 'none';
      }
    }

    // ── Countdown global tick ──────────────────────────────────────────────
    function pad2(n) { return n < 10 ? '0' + n : '' + n; }
    function tickCountdowns() {
      var now = Date.now();
      document.querySelectorAll('.drop-card__countdown[data-target]').forEach(function(el) {
        var target = parseInt(el.getAttribute('data-target'), 10);
        var diff = target - now;
        if (diff <= 0) {
          el.textContent = 'DISPO MAINTENANT';
          el.classList.add('drop-card__countdown--dispo');
        } else {
          var totalSec = Math.floor(diff / 1000);
          var days = Math.floor(totalSec / 86400);
          var hrs  = Math.floor((totalSec % 86400) / 3600);
          var mins = Math.floor((totalSec % 3600) / 60);
          var secs = totalSec % 60;
          var txt = (days > 0 ? days + 'J ' : '') + pad2(hrs) + ':' + pad2(mins) + ':' + pad2(secs);
          el.textContent = '⏱ ' + txt;
        }
      });
    }
    setInterval(tickCountdowns, 1000);
    tickCountdowns();

    window._render = render;
    document.querySelectorAll('.filter-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        document.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
        btn.classList.add('active');
        activeFilter = btn.dataset.brand;
        render();
      });
    });

    fetch(RELEASES_URL)
      .then(function(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function(data) {
        if (loading) loading.style.display = 'none';
        allReleases = data.filter(function(r) { return r.id && !r.id.startsWith('test-'); });
        window._releases = allReleases.slice();
        window.allReleases = allReleases;
        // Enrichir la recherche avec releases_past.json
        fetch('https://raw.githubusercontent.com/sneakerdropfr/sneakerdropfr.github.io/main/releases_past.json?t=' + Date.now())
          .then(function(res) { return res.json(); })
          .catch(function() { return []; })
          .then(function(past) {
            var seenIds = {};
            window._releases.forEach(function(r) { seenIds[r.id] = true; });
            past.forEach(function(r) { if (r.id && !seenIds[r.id]) window._releases.push(r); });
            window.allReleases = window._releases.slice();
          });

        // Section Raffles — compact: 1 card visible
        (function() {
          var raffles = allReleases.filter(function(r) { return r.raffle === true; }).sort(function(a,b){ var da=a.date||'9999'; var db=b.date||'9999'; return da<db?-1:da>db?1:(a.id||'').localeCompare(b.id||''); });
          var section = document.getElementById('raffle-section');
          var grid = document.getElementById('raffle-grid'); // kept for JS compat, hidden
          var compact = document.getElementById('raffle-compact');
          if (!section || !raffles.length) return;
          section.style.display = 'block';
          // Full grid (hidden, JS compat)
          if (grid) {
            grid.innerHTML = raffles.map(function(r) {
              var dateStr = '';
              if (r.date && r.date !== 'TBD') {
                var p = r.date.split('-');
                var d = new Date(parseInt(p[0]), parseInt(p[1])-1, parseInt(p[2]));
                dateStr = 'Drop le ' + d.toLocaleDateString('fr-FR', {day:'numeric', month:'long', year:'numeric'});
              }
              var price = r.price ? r.price + '' : '';
              return '<div class="raffle-card">'
                + '<div class="raffle-card__img"><img src="' + (r.image_url||'') + '" alt="' + (r.title||'').replace(/"/g,'') + '" loading="lazy"></div>'
                + '<div class="raffle-card__body">'
                + '<span class="raffle-card__badge">Raffle</span>'
                + '<div class="raffle-card__title">' + escapeHtml(r.title) + '</div>'
                + '<div class="raffle-card__meta">' + dateStr + (price ? ' · ' + price : '') + '</div>'
                + '<a href="' + (r.raffle_url||'#') + '" target="_blank" rel="noopener" class="raffle-card__btn">Participer au raffle</a>'
                + '</div></div>';
            }).join('');
          }
          // Carousel : toutes les raffles en scroll horizontal
          if (compact) {
            var carouselHtml = '<div class="raffle-carousel">';
            raffles.forEach(function(rf) {
              var dateStrRf = '';
              if (rf.date && rf.date !== 'TBD') {
                var prf = rf.date.split('-');
                var drf = new Date(parseInt(prf[0]), parseInt(prf[1])-1, parseInt(prf[2]));
                dateStrRf = 'Drop le ' + drf.toLocaleDateString('fr-FR', {day:'numeric', month:'long'});
              }
              var rfLink = rf.id ? 'sorties/' + rf.id + '.html' : (rf.raffle_url || rf.wtc_url || '#');
              carouselHtml += '<div class="raffle-carousel-item">'
                + (rf.image_url ? '<img src="' + rf.image_url + '" alt="' + escapeHtml(rf.title) + '" class="raffle-carousel-item__img" loading="lazy">' : '<div class="raffle-carousel-item__img"></div>')
                + '<div class="raffle-carousel-item__body">'
                + '<span class="raffle-carousel-item__badge">Raffle</span>'
                + '<div class="raffle-carousel-item__title">' + escapeHtml(rf.title) + '</div>'
                + '<div class="raffle-carousel-item__meta">' + dateStrRf + '</div>'
                + '<a href="' + rfLink + '" class="raffle-carousel-item__btn">Voir les raffles</a>'
                + '</div></div>';
            });
            carouselHtml += '</div>';
            compact.innerHTML = carouselHtml;
          }
        })();

        if (!allReleases.length) { if (empty) empty.style.display = 'block'; return; }
        var upcoming = allReleases.filter(function(r) { return isFutureOrToday(r.date); });
        var byScore = sortByScore(upcoming);
        renderTopPick(byScore[0]);
        render();
      })
      .catch(function(err) {
        if (loading) loading.style.display = 'none';
        console.error('Erreur releases:', err);
        if (empty) empty.style.display = 'block';
      });
  })();