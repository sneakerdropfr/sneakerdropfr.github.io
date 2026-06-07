(function() {
    var MONTHS_FR = ['','jan','fév','mar','avr','mai','juin','juil','août','sep','oct','nov','déc'];
    function formatDateFr(d) {
      if (!d) return '';
      var parts = d.split('-');
      if (parts.length === 3) { var m = parseInt(parts[1]); return parseInt(parts[2]) + ' ' + (MONTHS_FR[m] || ''); }
      return d;
    }
    function safeTitle(t) { return (t || '').replace(/'/g, "\\'").replace(/"/g, '&quot;'); }
    function buildBstnCard(p) {
      var nom = p.nom || '';
      var marque = p.marque || '';
      var prix = p.prix || '';
      var img = p.image_url || '';
      var aff = p.lien_affilie || p.lien_produit || '';
      var dateFr = formatDateFr(p.date || '');
      var couleur = p.couleur || '';
      var nomDisplay = nom;
      if (couleur && nom.toLowerCase().indexOf(couleur.toLowerCase()) === -1) nomDisplay = nom + ' (' + couleur + ')';
      return '<div class="drop-card">'
        + '<div class="drop-card__img-wrap">'
        + (img ? '<img src="' + img + '" alt="' + nom.replace(/"/g,'') + '" loading="lazy" style="width:100%;height:100%;object-fit:contain;background:#F9F9F9">' : '')
        + '<div class="drop-card__badge-top badge-upcoming">BSTN à venir</div>'
        + '</div>'
        + '<div class="drop-card__body">'
        + '<div class="drop-card__brand">' + marque.toUpperCase() + '</div>'
        + '<div class="drop-card__title">' + nomDisplay + '</div>'
        + '<div class="drop-card__meta">'
        + '<span class="drop-card__price">' + prix + '</span>'
        + (dateFr ? '<span class="drop-card__stock drop-card__stock--upcoming">Drop ' + dateFr + '</span>' : '')
        + '</div>'
        + (aff ? '<div class="drop-card__cta"><a href="' + aff + '" target="_blank" rel="nofollow noopener" class="btn-cop">Voir sur BSTN</a></div>' : '')
        + '</div>'
        + '</div>';
    }
    fetch('/bstn_upcoming.json?t=' + Date.now())
      .then(function(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function(products) {
        var _n = new Date();
        var today = _n.getFullYear() + '-' + String(_n.getMonth()+1).padStart(2,'0') + '-' + String(_n.getDate()).padStart(2,'0');
        var upcoming = products.filter(function(p) { return !p.date || p.date > today; });
        var grid = document.getElementById('bstn-upcoming-grid');
        var count = document.getElementById('bstn-upcoming-count');
        if (count) count.textContent = 'Paires à venir sur BSTN — ' + upcoming.length + ' drops confirmés';
        if (grid) grid.innerHTML = upcoming.length ? upcoming.map(buildBstnCard).join('') : '<p style="color:var(--muted);text-align:center;padding:2rem;grid-column:1/-1">Aucun drop à venir</p>';
      })
      .catch(function(e) {
        fetch('https://raw.githubusercontent.com/sneakerdropfr/sneakerdropfr.github.io/main/bstn_upcoming.json?t=' + Date.now())
          .then(function(r) { return r.json(); })
          .then(function(products) {
            var today = new Date().toISOString().substring(0,10);
            var upcoming = products.filter(function(p) { return !p.date || p.date >= today; });
            var grid = document.getElementById('bstn-upcoming-grid');
            var count = document.getElementById('bstn-upcoming-count');
            if (count) count.textContent = 'Paires à venir sur BSTN — ' + upcoming.length + ' drops confirmés';
            if (grid) grid.innerHTML = upcoming.length ? upcoming.map(buildBstnCard).join('') : '<p style="color:var(--muted);text-align:center;padding:2rem;grid-column:1/-1">Aucun drop à venir</p>';
          })
          .catch(function() {
            var grid = document.getElementById('bstn-upcoming-grid');
            if (grid) grid.innerHTML = '<p style="color:var(--muted);text-align:center;padding:2rem;grid-column:1/-1">Données non disponibles</p>';
          });
      });
  })();