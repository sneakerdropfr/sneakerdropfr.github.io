#!/usr/bin/env python3
"""Generate individual /sorties/{id}.html pages from releases.json.

Default behaviour: only generate pages that don't already exist (safe, never
overwrites curated content). Pass --force to regenerate every page listed in
releases.json. Pass --update-sitemap to add any newly-generated pages to
sitemap.xml.

Uses only fields present in releases.json. No invented sneaker data: the
"Notre avis" paragraph is a factual, generic sentence built from existing
fields (title, formatted date, price). Pages without retail/buy info are
still generated but include no retailers block.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from html import escape

ROOT = os.path.dirname(os.path.abspath(__file__))
SORTIES_DIR = os.path.join(ROOT, "sorties")
RELEASES_PATH = os.path.join(ROOT, "releases.json")
SITEMAP_PATH = os.path.join(ROOT, "sitemap.xml")
SITE_BASE = "https://sneakerdropfr.fr"

FR_DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
FR_MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def format_date_fr(iso: str | None) -> str:
    if not iso or iso == "TBD":
        return "TBD"
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", iso)
    if not m:
        return iso
    try:
        d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return iso
    return f"{FR_DAYS[d.weekday()]} {d.day} {FR_MONTHS[d.month - 1]} {d.year}"


def format_price(price) -> str:
    if price is None or price == "" or price == "TBD":
        return "TBD"
    return str(price)


def short_meta_desc(r: dict) -> str:
    title = r.get("title", "").strip()
    date_fr = format_date_fr(r.get("date"))
    price = format_price(r.get("price"))
    parts = [title]
    if date_fr != "TBD":
        parts.append(f"Sortie : {date_fr}")
    if price != "TBD":
        parts.append(f"Prix : {price}")
    cw = (r.get("colorway") or "").strip()
    if cw:
        parts.append(f"Colorway : {cw}")
    parts.append("Retrouve les liens d'achat et infos sur SneakerDrop FR.")
    return " — ".join(parts)


def editorial_text(r: dict) -> str:
    """Factual editorial block built from available release data. No invented content."""
    title = r.get("title", "").strip()
    brand = (r.get("brand") or "").strip()
    colorway = (r.get("colorway") or "").strip()
    date_fr = format_date_fr(r.get("date"))
    price = format_price(r.get("price"))
    raffle = r.get("raffle")
    resell = r.get("resell")
    rets = r.get("retailers") or []
    retail_names = [rt["name"] for rt in rets if rt.get("name") and not rt.get("resell")]
    resell_names = [rt["name"] for rt in rets if rt.get("name") and rt.get("resell")]

    parts = []

    # Phrase 1 — présentation
    intro = f"La <strong>{escape(title)}</strong>"
    if brand and brand.lower() not in title.lower():
        intro += f" est une paire signée <strong>{escape(brand)}</strong>"
    if colorway:
        intro += f" disponible dans le coloris <strong>{escape(colorway)}</strong>"
    intro += "."
    parts.append(intro)

    # Phrase 2 — date et prix
    if date_fr != "TBD" and price != "TBD":
        parts.append(f"Elle sort le <strong>{escape(date_fr)}</strong> au prix retail de <strong>{escape(price)}</strong>.")
    elif date_fr != "TBD":
        parts.append(f"La date de sortie est fixée au <strong>{escape(date_fr)}</strong>. Le prix retail n'a pas encore été communiqué.")
    elif price != "TBD":
        parts.append(f"Le prix retail est fixé à <strong>{escape(price)}</strong>. La date de sortie reste à confirmer.")
    else:
        parts.append("La date de sortie et le prix retail ne sont pas encore confirmés.")

    # Phrase 3 — raffle
    if raffle:
        parts.append("Une <strong>raffle</strong> est organisée pour cette sortie — inscris-toi tôt pour maximiser tes chances.")

    # Phrase 4 — resell
    if resell and str(resell).replace("€","").replace("$","").strip().isdigit():
        parts.append(f"Sur le marché secondaire, la paire s'échange autour de <strong>{escape(str(resell))}€</strong>.")

    # Phrase 5 — retailers
    if retail_names:
        if len(retail_names) == 1:
            parts.append(f"Tu peux l'acheter au prix retail chez <strong>{escape(retail_names[0])}</strong>.")
        else:
            listed = ", ".join(f"<strong>{escape(n)}</strong>" for n in retail_names[:-1])
            listed += f" et <strong>{escape(retail_names[-1])}</strong>"
            parts.append(f"Elle est disponible chez {listed}.")
    elif resell_names:
        parts.append("Aucun retailer officiel confirmé pour l'instant — des liens resell sont disponibles ci-dessous.")

    return " ".join(parts)


def retailers_html(r: dict) -> str:
    rets = r.get("retailers") or []
    if not rets and r.get("buy_url"):
        rets = [{"name": "Site officiel", "url": r["buy_url"], "price": r.get("price"), "resell": False}]
    if not rets:
        return ""
    rows = []
    for ret in rets:
        name = escape(str(ret.get("name", "Retailer")))
        url = ret.get("url") or ""
        if not url:
            continue
        price = ret.get("price")
        price_html = (
            f'<span class="retailer__price">{escape(str(price))}</span>'
            if price else ""
        )
        resell = ret.get("resell")
        badge = (
            '<span class="retailer__badge retailer__badge--resell">Resell</span>'
            if resell else
            '<span class="retailer__badge retailer__badge--retail">Retail</span>'
        )
        rows.append(
            '<a class="retailer" href="' + escape(url, quote=True) + '" '
            'target="_blank" rel="noopener nofollow sponsored">'
            f'<span class="retailer__name">{name}</span>'
            f'{price_html}{badge}'
            '<span class="retailer__arrow">→</span>'
            '</a>'
        )
    if not rows:
        return ""
    return (
        '<section class="article__retailers">'
        '<h2>Où <span>acheter</span></h2>'
        '<div class="retailers-list">' + "".join(rows) + '</div>'
        '</section>'
    )


def primary_buy_button(r: dict) -> str:
    rets = r.get("retailers") or []
    retail = next((x for x in rets if x.get("url") and not x.get("resell")), None)
    target = retail or (rets[0] if rets else None)
    url = (target and target.get("url")) or r.get("buy_url") or r.get("wtc_url")
    if not url:
        return ""
    label = "Acheter maintenant"
    return (
        '<a class="article__buy" href="' + escape(url, quote=True) + '" '
        f'target="_blank" rel="noopener nofollow sponsored">{label} →</a>'
    )


PAGE_TMPL = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{meta_title}</title>
  <meta name="description" content="{meta_desc}" />
  <link rel="canonical" href="{canonical}" />
  <meta property="og:title" content="{title_html} — SneakerDrop FR" />
  <meta property="og:description" content="{og_desc}" />
  <meta property="og:image" content="{og_image}" />
  <meta property="og:url" content="{canonical}" />
  <meta property="og:type" content="article" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{title_html} — SneakerDrop FR" />
  <meta name="twitter:description" content="{og_desc}" />
  <meta name="twitter:image" content="{og_image}" />
  <script type="application/ld+json">{jsonld}</script>
  <link rel="icon" href="/favicon.ico" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;600;700;900&family=Barlow+Condensed:wght@400;600;700;900&family=Bebas+Neue&display=swap" rel="stylesheet" />
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{
      --accent:#FF2D2D;--black:#0A0A0A;--white:#FFFFFF;--bg:#FFFFFF;--bg-alt:#F5F5F5;
      --text:#0A0A0A;--muted:#777;--border:#E5E5E5;
      --shadow:0 2px 12px rgba(0,0,0,0.07);--shadow-hover:0 8px 28px rgba(0,0,0,0.11);
      --r:12px;
      --font-display:'Bebas Neue',sans-serif;
      --font-body:'Barlow',sans-serif;
      --font-cond:'Barlow Condensed',sans-serif;
    }}
    html{{scroll-behavior:smooth}}
    body{{background:var(--bg);color:var(--text);font-family:var(--font-body);-webkit-font-smoothing:antialiased;overflow-x:hidden}}
    a{{text-decoration:none;color:inherit}}
    img{{max-width:100%;display:block}}
    .container{{max-width:1100px;margin:0 auto;padding:0 1.5rem}}
    .header{{position:sticky;top:0;z-index:100;background:rgba(255,255,255,.97);backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}}
    .header__inner{{display:flex;align-items:center;gap:.75rem;height:56px}}
    .logo{{display:flex;align-items:center;gap:.45rem;font-family:var(--font-cond);font-size:1.15rem;font-weight:900;letter-spacing:.04em;color:var(--black);flex-shrink:0}}
    .logo__icon{{width:30px;height:30px;background:transparent;border-radius:0;display:flex;align-items:center;justify-content:center;flex-shrink:0}}
    .logo__fr{{opacity:.45}}
    .header__spacer{{flex:1}}
    .header__nav{{display:flex;align-items:center;gap:.5rem}}
    .hbtn{{font-family:var(--font-cond);font-weight:900;font-size:.82rem;letter-spacing:.06em;text-transform:uppercase;padding:.42rem .9rem;border-radius:6px;white-space:nowrap;transition:background .15s,color .15s,border-color .15s;cursor:pointer;display:inline-flex;align-items:center;gap:.3rem;text-decoration:none}}
    .hbtn--solid{{background:var(--black);color:#fff;border:1px solid var(--black)}}
    .hbtn--solid:hover{{background:var(--accent);color:var(--black);border-color:var(--accent)}}
    .hbtn--tg{{background:var(--accent);color:#fff;border:1px solid var(--accent)}}
    .hbtn--tg:hover{{background:#cc2222;border-color:#cc2222}}
    @media(max-width:640px){{.hbtn--hide-sm{{display:none}}}}
    .article-wrap{{padding:3rem 0 5rem}}
    .article__back{{display:inline-flex;align-items:center;gap:.5rem;font-family:var(--font-cond);font-size:.85rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);margin-bottom:2rem;transition:color .15s}}
    .article__back:hover{{color:var(--black)}}
    .article__back svg{{width:16px;height:16px;flex-shrink:0}}
    .article__hero{{display:grid;grid-template-columns:1fr 1fr;gap:3rem;align-items:center;margin-bottom:3rem}}
    @media(max-width:768px){{.article__hero{{grid-template-columns:1fr}}}}
    .article__img-wrap{{background:#F5F5F5;border:1px solid var(--border);border-radius:16px;overflow:hidden;aspect-ratio:1;display:flex;align-items:center;justify-content:center;padding:1.5rem}}
    .article__img{{width:100%;height:100%;object-fit:contain}}
    .article__brand{{font-family:var(--font-cond);font-size:.75rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);margin-bottom:.5rem}}
    .article__title{{font-family:var(--font-display);font-size:clamp(2rem,5vw,3.2rem);text-transform:uppercase;line-height:1;color:var(--black);margin-bottom:.75rem}}
    .article__colorway{{font-family:var(--font-cond);color:var(--muted);font-size:.95rem;margin-bottom:1rem;letter-spacing:.03em}}
    .article__infos{{display:flex;flex-direction:column;gap:.65rem;margin-bottom:1.5rem}}
    .article__info-row{{display:flex;align-items:center;gap:1rem;padding:.85rem 1.1rem;background:var(--bg-alt);border:1px solid var(--border);border-radius:10px}}
    .article__info-label{{font-family:var(--font-cond);font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);min-width:70px}}
    .article__info-value{{font-family:var(--font-cond);font-size:1rem;font-weight:900;color:var(--black)}}
    .article__price-badge{{display:inline-block;padding:.5rem 1.2rem;background:var(--black);border-radius:8px;font-family:var(--font-display);font-size:1.4rem;color:#fff;margin-bottom:.75rem}}
    .article__buy{{display:inline-flex;align-items:center;gap:.4rem;background:var(--accent);color:#fff;font-family:var(--font-cond);font-weight:900;font-size:.9rem;letter-spacing:.06em;text-transform:uppercase;padding:.65rem 1.4rem;border-radius:8px;margin-top:.5rem;transition:background .15s,transform .15s}}
    .article__buy:hover{{background:#cc2222;transform:translateY(-1px)}}
    .article__editorial{{background:var(--bg-alt);border:1px solid var(--border);border-radius:16px;padding:2rem;margin-bottom:2.5rem}}
    .article__editorial h2{{font-family:var(--font-display);font-size:1.4rem;text-transform:uppercase;color:var(--black);margin-bottom:1rem;letter-spacing:.03em}}
    .article__editorial h2 span{{color:var(--accent)}}
    .article__editorial p,.article__editorial div{{color:#333;line-height:1.75;font-size:.95rem}}
    .article__retailers{{margin-bottom:2.5rem}}
    .article__retailers h2{{font-family:var(--font-display);font-size:1.6rem;text-transform:uppercase;letter-spacing:.03em;margin-bottom:1rem}}
    .article__retailers h2 span{{color:var(--accent)}}
    .retailers-list{{display:flex;flex-direction:column;gap:.6rem}}
    .retailer{{display:flex;align-items:center;gap:1rem;padding:.95rem 1.2rem;background:#fff;border:1px solid var(--border);border-radius:10px;transition:border-color .15s,transform .15s,box-shadow .15s}}
    .retailer:hover{{border-color:var(--black);transform:translateY(-1px);box-shadow:var(--shadow)}}
    .retailer__name{{font-family:var(--font-cond);font-weight:900;font-size:1rem;letter-spacing:.04em;text-transform:uppercase;flex:1}}
    .retailer__price{{font-family:var(--font-cond);font-weight:700;font-size:.95rem;color:var(--black)}}
    .retailer__badge{{font-family:var(--font-cond);font-size:.7rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;padding:.2rem .55rem;border-radius:999px}}
    .retailer__badge--retail{{background:#E6F4EA;color:#137333}}
    .retailer__badge--resell{{background:#FCE8E6;color:#A50E0E}}
    .retailer__arrow{{font-family:var(--font-cond);font-weight:900;color:var(--muted)}}
    .article__cta{{background:var(--black);border-radius:16px;padding:2.5rem;text-align:center;color:#fff}}
    .article__cta h3{{font-family:var(--font-display);font-size:1.6rem;text-transform:uppercase;letter-spacing:.03em;margin-bottom:.6rem}}
    .article__cta p{{color:rgba(255,255,255,.6);font-size:.9rem;margin-bottom:1.5rem}}
    .btn-tg{{display:inline-flex;align-items:center;gap:.5rem;background:var(--accent);color:#fff;font-family:var(--font-cond);font-weight:900;font-size:.95rem;letter-spacing:.07em;text-transform:uppercase;padding:.8rem 1.8rem;border-radius:8px;transition:background .15s,transform .15s}}
    .btn-tg:hover{{background:#cc2222;transform:translateY(-2px)}}
    .footer{{background:var(--bg-alt);border-top:1px solid var(--border);padding:2rem 0}}
    .footer__inner{{display:flex;align-items:center;flex-wrap:wrap;gap:1rem;justify-content:space-between}}
    .footer__copy{{font-size:.82rem;color:var(--muted);flex:1;min-width:200px}}
    .footer__links{{display:flex;gap:1rem}}
    .footer__links a{{font-family:var(--font-cond);font-size:.78rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);transition:color .15s}}
    .footer__links a:hover{{color:var(--black)}}
  </style>
</head>
<body>
  <header class="header">
    <div class="container header__inner">
      <a href="/" class="logo">
        <div class="logo__icon"><img src="/assets/images/sneakerdropfr-logo.svg" alt="SneakerDropFR" width="30" height="30" style="display:block"></div>
        <span>SneakerDrop<span class="logo__fr">FR</span></span>
      </a>
      <div class="header__spacer"></div>
      <nav class="header__nav">
        <a href="/deals.html" class="hbtn hbtn--solid hbtn--hide-sm">BSTN Deals</a>
        <a href="/sorties.html" class="hbtn hbtn--solid hbtn--hide-sm">Sorties</a>
        <a href="https://t.me/SneakersDropsFR" target="_blank" rel="noopener" class="hbtn hbtn--tg">Telegram</a>
      </nav>
    </div>
  </header>

  <main class="article-wrap">
    <div class="container">
      <a href="/sorties.html" class="article__back">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M19 12H5M12 5l-7 7 7 7"/></svg>
        Toutes les sorties
      </a>

      <div class="article__hero">
        <div class="article__img-wrap">
          {img_tag}
        </div>
        <div>
          <div class="article__brand">{brand_html}</div>
          <h1 class="article__title">{title_html}</h1>
          {colorway_html}
          <div class="article__infos">
            <div class="article__info-row">
              <span class="article__info-label">Date</span>
              <span class="article__info-value">{date_fr}</span>
            </div>
            <div class="article__info-row">
              <span class="article__info-label">Prix</span>
              <span class="article__info-value">{price_html}</span>
            </div>
          </div>
          <div class="article__price-badge">{price_html}</div>
          {buy_btn}
        </div>
      </div>

      <div class="article__editorial">
        <h2>Notre <span>avis</span></h2>
        <div>{editorial}</div>
      </div>

      {retailers_block}

      <div class="article__cta">
        <h3>Sois le premier alerté</h3>
        <p>Rejoins le canal Telegram — restocks, promos et drops en temps réel, 24h/24.</p>
        <a href="https://t.me/SneakersDropsFR" target="_blank" rel="noopener" class="btn-tg">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12L7.14 13.745l-2.96-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.834.814h-.826z"/></svg>
          Rejoindre gratuitement
        </a>
      </div>
    </div>
  </main>

  <footer class="footer">
    <div class="container">
      <div class="footer__inner">
        <a href="/" class="logo">
          <div class="logo__icon" style="width:26px;height:26px"><img src="/assets/images/sneakerdropfr-logo.svg" alt="SneakerDropFR" width="26" height="26" style="display:block"></div>
          <span style="font-size:1rem">SneakerDrop<span class="logo__fr">FR</span></span>
        </a>
        <p class="footer__copy">Veille sneakers — alertes restocks, promos et drops en temps réel.</p>
        <div class="footer__links">
          <a href="https://t.me/SneakersDropsFR" target="_blank" rel="noopener">Telegram</a>
          <a href="https://www.tiktok.com/@sneakerdropfr" target="_blank" rel="noopener">TikTok</a>
          <a href="https://www.instagram.com/sneakerdropfr/" target="_blank" rel="noopener">Instagram</a>
        </div>
      </div>
      <div style="margin-top:.75rem;font-size:.75rem;color:var(--muted)"><a href="/privacy.html" style="color:var(--muted)">Politique de confidentialité</a> — <a href="/sitemap.xml" style="color:var(--muted)">Sitemap</a></div>
    </div>
  </footer>

  <script type="text/javascript" src="https://s.skimresources.com/js/302926X179095.skimlinks.js"></script>
</body>
</html>
"""


def render_page(r: dict) -> str:
    rid = r.get("id", "")
    title = r.get("title", "").strip() or rid
    brand = (r.get("brand") or "").strip()
    cw = (r.get("colorway") or "").strip()
    date_fr = format_date_fr(r.get("date"))
    price = format_price(r.get("price"))
    image_url = (r.get("image_url") or "").strip()
    canonical = f"{SITE_BASE}/sorties/{rid}.html"

    title_html = escape(title)
    brand_html = escape(brand) if brand else "Sneakers"
    price_html = escape(price)
    meta_desc = escape(short_meta_desc(r), quote=True)
    og_desc_parts = []
    if date_fr != "TBD":
        og_desc_parts.append(f"Sortie : {date_fr}")
    if price != "TBD":
        og_desc_parts.append(f"Prix : {price}")
    og_desc = escape(" — ".join(og_desc_parts) or title, quote=True)
    og_image = escape(image_url or f"{SITE_BASE}/assets/images/sneakerdropfr-logo.svg", quote=True)

    colorway_html = (
        f'<p class="article__colorway">{escape(cw)}</p>' if cw else ""
    )

    if image_url:
        img_tag = (
            '<img src="' + escape(image_url, quote=True) + '" '
            f'alt="{title_html}" class="article__img" loading="lazy" '
            'onerror="this.parentElement.style.background=\'#eee\';this.style.display=\'none\'">'
        )
    else:
        img_tag = '<div style="font-size:4rem">👟</div>'

    # Meta title optimisé < 60 chars
    suffix = " | SneakerDrop FR"
    base_title = title
    max_base = 60 - len(suffix)
    if len(base_title) > max_base:
        base_title = base_title[:max_base].rsplit(" ", 1)[0]
    meta_title = escape(base_title + suffix)

    jsonld_obj = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": title,
        "brand": {"@type": "Brand", "name": brand} if brand else None,
        "image": image_url or None,
        "description": short_meta_desc(r),
        "url": canonical,
    }
    if cw:
        jsonld_obj["color"] = cw
    offers = None
    rets = r.get("retailers") or []
    if rets:
        offer_list = []
        for ret in rets:
            url = ret.get("url")
            if not url:
                continue
            offer = {
                "@type": "Offer",
                "url": url,
                "seller": {"@type": "Organization", "name": ret.get("name", "Retailer")},
                "availability": "https://schema.org/PreOrder",
            }
            p = ret.get("price")
            if isinstance(p, str) and p:
                offer["price"] = re.sub(r"[^\d.,]", "", p).replace(",", ".") or None
                offer["priceCurrency"] = "EUR" if "€" in p else ("USD" if "$" in p else "EUR")
                if not offer["price"]:
                    offer.pop("price", None)
                    offer.pop("priceCurrency", None)
            offer_list.append(offer)
        if offer_list:
            offers = offer_list
    elif r.get("buy_url"):
        offers = [{"@type": "Offer", "url": r["buy_url"]}]
    if offers:
        jsonld_obj["offers"] = offers
    jsonld_obj = {k: v for k, v in jsonld_obj.items() if v is not None}
    jsonld = json.dumps(jsonld_obj, ensure_ascii=False).replace("</", "<\\/")

    return PAGE_TMPL.format(
        meta_title=meta_title,
        title_html=title_html,
        meta_desc=meta_desc,
        canonical=escape(canonical, quote=True),
        og_desc=og_desc,
        og_image=og_image,
        jsonld=jsonld,
        img_tag=img_tag,
        brand_html=brand_html,
        colorway_html=colorway_html,
        date_fr=escape(date_fr),
        price_html=price_html,
        buy_btn=primary_buy_button(r),
        editorial=editorial_text(r),
        retailers_block=retailers_html(r),
    )


def update_sitemap(new_ids: list[str]) -> int:
    if not new_ids:
        return 0
    if not os.path.exists(SITEMAP_PATH):
        return 0
    with open(SITEMAP_PATH, "r", encoding="utf-8") as f:
        sm = f.read()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    added = 0
    insertion = []
    for rid in new_ids:
        url = f"{SITE_BASE}/sorties/{rid}.html"
        if url in sm:
            continue
        insertion.append(
            "  <url>\n"
            f"    <loc>{url}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            "    <changefreq>weekly</changefreq>\n"
            "    <priority>0.6</priority>\n"
            "  </url>\n"
        )
        added += 1
    if not insertion:
        return 0
    sm = sm.replace("</urlset>", "".join(insertion) + "</urlset>")
    with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
        f.write(sm)
    return added


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing /sorties/{id}.html files.")
    ap.add_argument("--update-sitemap", action="store_true",
                    help="Append newly created URLs to sitemap.xml.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print plan, do not write files.")
    args = ap.parse_args()

    with open(RELEASES_PATH, "r", encoding="utf-8") as f:
        releases = json.load(f)

    os.makedirs(SORTIES_DIR, exist_ok=True)
    existing = set(os.listdir(SORTIES_DIR))

    created, overwrote, skipped = [], [], []
    for r in releases:
        rid = r.get("id", "")
        if not rid:
            skipped.append("(missing id)")
            continue
        fname = f"{rid}.html"
        path = os.path.join(SORTIES_DIR, fname)
        is_new = fname not in existing
        if not is_new and not args.force:
            skipped.append(rid)
            continue
        html = render_page(r)
        if args.dry_run:
            (created if is_new else overwrote).append(rid)
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        (created if is_new else overwrote).append(rid)

    print(f"Created: {len(created)}")
    print(f"Overwrote: {len(overwrote)}")
    print(f"Skipped (already exist; pass --force to overwrite): {len(skipped)}")
    if args.update_sitemap and not args.dry_run:
        added = update_sitemap(created)
        print(f"Added to sitemap: {added}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
