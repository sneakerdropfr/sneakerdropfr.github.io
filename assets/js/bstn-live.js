var BSTN_AWIN_MID = '104979';
  var BSTN_AWIN_AFF = '2855487';
  var BSTN_API_URL  = 'https://searcht.bstn.com/collections/magento2_eu_products/documents/search';
  var BSTN_API_KEY  = 'NCZstZEMLnMy4MSLPh9NKNrtMLsEF1Zy';
  var BSTN_SITE     = 'https://www.bstn.com/';
  var _bstnCache    = {};
  function bstnAwinUrl(productPath) {
    return 'https://www.awin1.com/cread.php?awinmid=' + BSTN_AWIN_MID + '&awinaffid=' + BSTN_AWIN_AFF + '&p=' + encodeURIComponent(BSTN_SITE + productPath);
  }
  function bstnCheckSku(sku, cb) {
    if (!sku) return;
    var skuKey = sku.toLowerCase();
    if (_bstnCache[skuKey] !== undefined) { if (_bstnCache[skuKey]) cb(_bstnCache[skuKey]); return; }
    var skuNorm = skuKey.replace(/-/g, '');
    var q = skuKey.replace(/-/g, ' ');
    var url = BSTN_API_URL + '?q=' + encodeURIComponent(q) + '&query_by=name&per_page=5&filter_by=price%3A%3E0';
    fetch(url, { headers: { 'X-TYPESENSE-API-KEY': BSTN_API_KEY } })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var hits = data.hits || [];
        for (var i = 0; i < hits.length; i++) {
          var doc = hits[i].document;
          var docUrl = (doc.url || '').toLowerCase();
          if (docUrl.indexOf(skuNorm) !== -1) {
            var awinUrl = bstnAwinUrl(doc.url);
            _bstnCache[skuKey] = awinUrl; cb(awinUrl); return;
          }
        }
        _bstnCache[skuKey] = null;
      }).catch(function() { _bstnCache[skuKey] = null; });
  }
  function bstnInjectBtn(container, awinUrl, label) {
    if (!container || container.querySelector('.btn-bstn-aff')) return;
    var btn = document.createElement('a');
    btn.href = awinUrl; btn.target = '_blank'; btn.rel = 'noopener sponsored';
    btn.className = 'btn-bstn-aff'; btn.textContent = label || 'Acheter sur BSTN';
    btn.onclick = function() { trackBSTN(container.closest('[data-title]') ? container.closest('[data-title]').getAttribute('data-title') : 'bstn'); };
    container.appendChild(btn);
  }
  // Section catalogue (static hype cards)
  (function() {
    document.querySelectorAll('#panel-catalogue .drop-card[data-sku]').forEach(function(card) {
      var sku = card.getAttribute('data-sku');
      var cta = card.querySelector('.drop-card__cta');
      bstnCheckSku(sku, function(url) { bstnInjectBtn(cta, url, 'Acheter sur BSTN'); });
    });
  })();
  // Dynamic drop cards observer
  (function() {
    var observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(m) {
        m.addedNodes.forEach(function(node) {
          if (node.nodeType !== 1) return;
          var cards = node.matches && node.matches('.drop-card') ? [node] : Array.from(node.querySelectorAll('.drop-card[data-sku]'));
          cards.forEach(function(card) {
            var sku = card.getAttribute('data-sku');
            if (!sku) return;
            var ctaDiv = card.querySelector('.drop-card__cta');
            bstnCheckSku(sku, function(url) { bstnInjectBtn(ctaDiv, url, 'Acheter sur BSTN'); });
          });
        });
      });
    });
    var grids = ['releases-grid-week','releases-grid-upcoming','weekly-drops-grid','top-pick-card'];
    grids.forEach(function(id) { var el = document.getElementById(id); if (el) observer.observe(el, { childList: true, subtree: true }); });
  })();