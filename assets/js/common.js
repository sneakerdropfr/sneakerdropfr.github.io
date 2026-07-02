/* SneakerDrop FR — common.js
   GA4 + tracking partagé sur toutes les pages */

window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'G-1TQQ3RSJJV');

function trackBSTN(product) {
  if (typeof gtag !== 'undefined') {
    gtag('event', 'click_bstn', { event_category: 'outbound', event_label: product, value: 1 });
  }
  try {
    var clicks = JSON.parse(localStorage.getItem('sdf_clicks') || '{}');
    clicks[product] = (clicks[product] || 0) + 1;
    localStorage.setItem('sdf_clicks', JSON.stringify(clicks));
  } catch(e) {}
}

function trackTelegram(source) {
  if (typeof gtag !== 'undefined') {
    gtag('event', 'telegram_click', { event_category: 'engagement', event_label: source || 'unknown' });
  }
}

function trackOutbound(retailer, product) {
  if (typeof gtag !== 'undefined') {
    gtag('event', 'click_retailer', { event_category: 'outbound', event_label: retailer + ' | ' + product, value: 1 });
  }
}

/* ══ Dark Mode Toggle ══ */
(function(){
  var PREF_KEY = 'theme-pref';
  function applyTheme(dark){
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
    var btn = document.getElementById('theme-toggle');
    if(btn) btn.textContent = dark ? '☀️' : '🌙';
  }
  function initTheme(){
    var btn = document.getElementById('theme-toggle');
    var stored = localStorage.getItem(PREF_KEY);
    var prefersDark = stored !== null ? stored === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(prefersDark);
    if(btn){
      btn.addEventListener('click', function(){
        var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        var next = !isDark;
        applyTheme(next);
        localStorage.setItem(PREF_KEY, next ? 'dark' : 'light');
      });
    }
  }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', initTheme);
  } else {
    initTheme();
  }
})();
