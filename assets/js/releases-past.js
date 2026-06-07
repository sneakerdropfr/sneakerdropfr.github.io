function renderPastGrid(data) {
    var grid = document.getElementById('past-grid');
    var btn = document.getElementById('btn-past');
    try {
      var hypePast = JSON.parse(localStorage.getItem('sdf_hype_past') || '[]');
      if (hypePast.length) {
        var existingIds = data.map(function(r) { return r.id; });
        hypePast.forEach(function(r) { if (existingIds.indexOf(r.id) === -1) data.unshift(r); });
      }
    } catch(e) {}
    if (!data.length) {
      grid.innerHTML = '<p style="text-align:center;color:var(--muted);padding:2rem">Aucune ancienne sortie disponible.</p>';
    } else {
      var html = '<div class="cards-grid">';
      data.forEach(function(r) {
        var img = r.image_url ? '<img src="' + r.image_url + '" class="drop-card__img" loading="lazy" onerror="this.style.display=\'none\'">' : '<div class="drop-card__img-placeholder"><svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 80 60' width='80' height='60'><rect width='80' height='60' fill='#F5F5F5'/><path d='M15 40 Q25 20 40 22 Q55 24 65 38 L65 42 Q55 48 40 46 Q25 44 15 42 Z' fill='#E0E0E0'/><path d='M30 22 L35 16 Q40 12 45 16 L50 22' fill='none' stroke='#CCC' stroke-width='2'/></svg></div>';
        html += '<article class="drop-card">';
        html += '<div class="drop-card__img-wrap">' + img + '</div>';
        html += '<div class="drop-card__body">';
        html += '<div class="drop-card__brand">' + (r.brand || r.source || '') + '</div>';
        html += '<h3 class="drop-card__title">' + escapeHtml(r.title) + '</h3>';
      // Badge hype_score
      if (r.hype_score && r.hype_score >= 40) {
        var hs = r.hype_score;
        var hsCls = hs >= 80 ? 'hype-score--hot' : hs >= 60 ? 'hype-score--hype' : 'hype-score--mid';
        var hsIcon = hs >= 80 ? '🔥' : hs >= 60 ? '⚡' : '●';
        html += '<div class="hype-score ' + hsCls + '">' + hsIcon + ' ' + hs + '/100</div>';
      }
        html += '<div class="drop-card__meta"><span>' + (r.date || 'TBD') + '</span><span class="drop-card__price">' + (r.price || '') + '</span></div>';
        html += '<a href="' + (r.link || '#') + '" target="_blank" rel="noopener" class="drop-card__cta btn-cop">Voir la paire</a>';
        html += '</div></article>';
      });
      html += '</div>';
      grid.innerHTML = html;
    }
    grid.style.display = 'block';
    btn.textContent = '🔼 Masquer les anciennes sorties';
  }
  function loadPastReleases() {
    var btn = document.getElementById('btn-past');
    var grid = document.getElementById('past-grid');
    if (grid.style.display === 'block') {
      grid.style.display = 'none';
      btn.textContent = '\u{1F550} Voir les anciennes sorties';
      return;
    }
    btn.textContent = 'Chargement...';
    var today = new Date(); today.setHours(0,0,0,0);
    // Paires passées depuis allReleases (releases.json)
    var fromActive = (window.allReleases || []).filter(function(r) {
      if (!r.date || r.date === 'TBD') return false;
      var p = r.date.split('-');
      if (p.length !== 3) return false;
      return new Date(+p[0], +p[1]-1, +p[2]) < today;
    });
    // Charger releases_past.json
    fetch('https://raw.githubusercontent.com/sneakerdropfr/sneakerdropfr.github.io/main/releases_past.json?t=' + Date.now())
      .then(function(res) { return res.json(); })
      .catch(function() { return []; })
      .then(function(pastData) {
        // Merger sans doublons (releases_past.json prioritaire)
        var seenIds = {};
        var merged = [];
        pastData.forEach(function(r) { if (r.id) { seenIds[r.id] = true; merged.push(r); } });
        fromActive.forEach(function(r) { if (r.id && !seenIds[r.id]) merged.push(r); });
        // Trier par date desc, TBD en dernier
        merged.sort(function(a, b) {
          if (!a.date || a.date === 'TBD') return 1;
          if (!b.date || b.date === 'TBD') return -1;
          return b.date.localeCompare(a.date);
        });
        renderPastGrid(merged);
      });
  }