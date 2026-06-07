function escapeHtml(t) { return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }


  (function(){
    var btn = document.getElementById('scroll-top');
    if (!btn) return;
    window.addEventListener('scroll', function(){
      btn.classList.toggle('visible', window.scrollY > 300);
    }, {passive:true});
  })();
  

  var _activeBrand = 'all';
  function setBrandFilter(brand, btn) {
    _activeBrand = brand;
    document.querySelectorAll('.brand-filter').forEach(function(b){ b.classList.remove('active'); });
    if (btn) btn.classList.add('active');
    // Connecter au système de filtre existant
    if (typeof activeFilter !== 'undefined') {
      activeFilter = brand === 'all' ? 'all' : brand.toLowerCase();
      if (typeof render === 'function') render();
    }
  }
  

  function copyCode(e, code) {
    e.preventDefault(); e.stopPropagation();
    navigator.clipboard.writeText(code).then(function(){
      var el = e.target;
      var orig = el.textContent;
      el.textContent = '✓ Copié !';
      el.style.background = 'rgba(255,255,255,.4)';
      setTimeout(function(){ el.textContent = orig; el.style.background = ''; }, 1500);
    });
  }
  

    (function(){
      try {
        fetch('https://track.sneakerdropfr.fr/pageview', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({page: window.location.pathname}),
          keepalive: true
        }).catch(function(){});
      } catch(e) {}
    })();