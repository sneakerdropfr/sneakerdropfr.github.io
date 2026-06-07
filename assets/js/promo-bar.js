(function() {
    var now = new Date();
    var today = now.toISOString().slice(0,10);
    var promos = [
      { code: 'SUMMER15', label: '-15% chez BSTN', start: '2026-05-29', end: '2026-05-31', icon: '⏰', prefix: 'Expire ce soir :' },
      { code: 'SPORT25',  label: '-25% Sportswear', start: '2026-06-02', end: '2026-06-03', icon: '⚽', prefix: '2–3 juin :' },
      { code: null,       label: '-30% Summer Sale →', start: '2026-05-25', end: '2026-06-07', icon: '🔥', prefix: "Jusqu'au 7 juin :" },
    ];
    var active = promos.filter(function(p){ return today >= p.start && today <= p.end; });
    if (active.length > 0) {
      var bar = document.getElementById('promo-bar');
      var inner = document.getElementById('promo-bar-inner');
      var parts = active.map(function(p, i) {
        var sep = i > 0 ? '<span class="promo-bar__sep">|</span>' : '';
        if (p.code) {
          return sep + '<a href="/bstn-promos.html" class="promo-bar__item"><span>' + p.icon + ' ' + p.prefix + '</span><span class="promo-bar__code" onclick="copyCode(event,\'' + p.code + '\')">' + p.code + '</span><span>= ' + p.label + '</span></a>';
        } else {
          return sep + '<a href="/bstn-promos.html" class="promo-bar__item"><span>' + p.icon + ' ' + p.prefix + ' ' + p.label + '</span></a>';
        }
      });
      inner.innerHTML = parts.join('');
      bar.style.display = 'block';
    }
  })();