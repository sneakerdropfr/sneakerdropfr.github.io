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
