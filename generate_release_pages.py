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
RELEASES_PAST_PATH = os.path.join(ROOT, "releases_past.json")
SITEMAP_PATH = os.path.join(ROOT, "sitemap.xml")
AFFILIATE_MAPPING_PATH = os.path.join(ROOT, "affiliate_mapping.json")
MANUAL_RETAILERS_PATH = os.path.join(ROOT, "manual_retailers.json")
SITE_BASE = "https://sneakerdropfr.fr"

# ── Affiliate config ──────────────────────────────────────────────────────────
AWIN_AFFID = "2855487"

# Charger affiliate_mapping.json (format domaine -> config)
def _load_awin_map() -> dict:
    try:
        with open(AFFILIATE_MAPPING_PATH, encoding="utf-8") as f:
            data = json.load(f)
        # Filtrer les clés privées (_comment, _awinaffid)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception:
        return {}

AWIN_MAP: dict = _load_awin_map()

# Charger manual_retailers.json
def _load_manual_retailers() -> dict:
    try:
        with open(MANUAL_RETAILERS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

MANUAL_RETAILERS: dict = _load_manual_retailers()


def build_awin_url(destination_url: str) -> str | None:
    """Construit un lien Awin si le domaine est actif dans affiliate_mapping.json.
    Retourne None si status != active, ou si le lien est déjà affilié.
    Ne modifie jamais un lien déjà affilié. Ne touche jamais aux pending.
    """
    if not destination_url:
        return None
    if "awin1.com" in destination_url or "awinmid" in destination_url:
        return destination_url  # déjà affilié, ne pas toucher
    try:
        from urllib.parse import urlparse, quote
        domain = urlparse(destination_url).netloc.lstrip("www.")
        config = AWIN_MAP.get(domain) or AWIN_MAP.get("www." + domain)
        if not config:
            return None
        if config.get("status") != "active":
            return None  # pending ou none → lien direct
        mid = config.get("awinmid") or config.get("awin_mid")
        if not mid:
            return None
        encoded = quote(destination_url, safe="")
        return (
            f"https://www.awin1.com/cread.php"
            f"?awinmid={mid}&awinaffid={AWIN_AFFID}&p={encoded}"
        )
    except Exception:
        return None

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
    s = str(price).strip()
    # Ajouter le symbole € si c'est un nombre sans devise
    if s.replace(".", "").replace(",", "").isdigit():
        return s + "\u00a0€"
    if s.endswith("€") or s.endswith("$") or s.endswith("£"):
        return s
    return s


def short_meta_desc(r: dict) -> str:
    title = r.get("title", "").strip()
    date_fr = format_date_fr(r.get("date"))
    price = format_price(r.get("price"))
    rets = r.get("retailers") or []
    retail_names = [rt.get("name","") for rt in rets if not rt.get("resell") and not rt.get("raffle")]
    desc = "Ou acheter " + title + " au prix retail"
    if price != "TBD":
        desc += " a " + price
    if date_fr != "TBD":
        desc += ". Sortie le " + date_fr
    if retail_names:
        desc += ". Disponible chez " + ", ".join(retail_names[:3])
        if len(retail_names) > 3:
            desc += " et " + str(len(retail_names)-3) + " autres retailers"
    desc += ". Liens et infos sur SneakerDrop FR."
    return desc


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


def get_retailers_for_release(r: dict) -> list:
    """Retourne les retailers dans l'ordre de priorité :
    1. manual_retailers.json
    2. retailers dans releases.json
    3. buy_url comme retailer unique
    4. liste vide (fallback wtc_url géré ailleurs)
    """
    rid = r.get("id", "")

    # Priorité 1 : manual_retailers.json
    if rid in MANUAL_RETAILERS and MANUAL_RETAILERS[rid]:
        return MANUAL_RETAILERS[rid]

    # Priorité 2 : retailers dans releases.json
    rets = r.get("retailers") or []
    # Filtrer les retailers avec URL valide et sans lien whentocop
    clean = [
        rt for rt in rets
        if rt.get("url") and "whentocop" not in rt.get("url", "").lower()
    ]
    if clean:
        return clean

    # Priorité 3 : buy_url comme retailer unique
    buy = r.get("buy_url", "")
    if buy and "whentocop" not in buy.lower():
        return [{"name": "Site officiel", "url": buy, "price": r.get("price"), "resell": False}]

    return []


def retailers_html(r: dict) -> str:
    rets = get_retailers_for_release(r)
    if not rets:
        return ""
        return ""

    def make_row(ret):
        name = escape(str(ret.get("name", "Retailer")))
        url = ret.get("url") or ""
        if not url:
            return ""
        is_resell = ret.get("resell") or ret.get("type") == "resell"
        is_raffle = ret.get("raffle") or ret.get("type") == "raffle" or ret.get("status") == "raffle"
        if not is_resell and not is_raffle:
            awin_url = build_awin_url(url)
            if awin_url:
                url = awin_url
        price = ret.get("price")
        price_html = (
            f'<span class="retailer__price">{escape(str(price))}</span>'
            if price and str(price) not in ("resell", "") else ""
        )
        badge = (
            '<span class="retailer__badge retailer__badge--resell">Resell</span>'
            if is_resell else
            '<span class="retailer__badge retailer__badge--raffle">Raffle</span>'
            if is_raffle else
            '<span class="retailer__badge retailer__badge--retail">Retail</span>'
        )
        return (
            '<a class="retailer" href="' + escape(url, quote=True) + '" '
            'target="_blank" rel="noopener nofollow sponsored">'
            f'<span class="retailer__name">{name}</span>'
            f'{price_html}{badge}'
            '<span class="retailer__arrow">→</span>'
            '</a>'
        )

    # Séparer en 3 groupes
    retail  = [rt for rt in rets if not (rt.get("resell") or rt.get("type")=="resell") and not (rt.get("raffle") or rt.get("type")=="raffle" or rt.get("status")=="raffle")]
    raffles = [rt for rt in rets if rt.get("raffle") or rt.get("type")=="raffle" or rt.get("status")=="raffle"]
    resell  = [rt for rt in rets if rt.get("resell") or rt.get("type")=="resell"]

    # ── Comparateur de prix ──────────────────────────────────────────────
    def parse_price_val(p) -> float | None:
        """Convertit '165€' ou '165' ou 165 en float."""
        if p is None:
            return None
        try:
            return float(str(p).replace('€','').replace('$','').replace(',','.').strip())
        except Exception:
            return None

    def price_comparator_html() -> str:
        retail_prices = [
            (rt.get('name',''), parse_price_val(rt.get('price')))
            for rt in rets
            if not (rt.get('resell') or rt.get('type')=='resell')
            and not (rt.get('raffle') or rt.get('type')=='raffle')
            and rt.get('price')
        ]
        resell_prices = [
            (rt.get('name',''), parse_price_val(rt.get('price')))
            for rt in rets
            if (rt.get('resell') or rt.get('type')=='resell')
            and rt.get('price')
        ]
        retail_prices = [(n,v) for n,v in retail_prices if v is not None]
        resell_prices = [(n,v) for n,v in resell_prices if v is not None]

        # Besoin d'au moins 1 retail ET 1 resell avec des prix pour afficher le comparateur
        if not retail_prices:
            return ''
        # Ou au moins 2 retailers retail avec prix différents
        retail_vals = [v for _,v in retail_prices]
        resell_vals = [v for _,v in resell_prices]

        retail_min = min(retail_vals)
        retail_max = max(retail_vals)

        if resell_vals:
            best_val = min(resell_vals)
            best_name = next(n for n,v in resell_prices if v == best_val)
            saving = retail_min - best_val
            saving_html = ''
            if saving > 0:
                saving_html = (f'<span class="price-comparator__saving">'
                               f'−{saving:.0f}€ vs retail</span>')
            elif saving < 0:
                saving_html = (f'<span class="price-comparator__saving" '
                               f'style="background:#FCE8E6;color:#A50E0E">'
                               f'+{abs(saving):.0f}€ vs retail</span>')
            return (
                '<div class="price-comparator">'
                '<div class="price-comparator__best">'
                '<span class="price-comparator__label">Prix retail</span>'
                f'<span class="price-comparator__value">{retail_min:.0f}€</span>'
                '</div>'
                '<div class="price-comparator__sep"></div>'
                '<div class="price-comparator__best">'
                '<span class="price-comparator__label">Meilleur prix</span>'
                f'<span class="price-comparator__value price-comparator__value--accent">{best_val:.0f}€</span>'
                '</div>'
                f'{saving_html}'
                f'<span class="price-comparator__source">{escape(best_name)}</span>'
                '</div>'
            )
        elif len(set(retail_vals)) > 1:
            # Plusieurs retailers retail avec prix différents : afficher le min
            best_val = retail_min
            best_name = next(n for n,v in retail_prices if v == best_val)
            return (
                '<div class="price-comparator">'
                '<div class="price-comparator__best">'
                '<span class="price-comparator__label">Prix retail</span>'
                f'<span class="price-comparator__value">{retail_max:.0f}€</span>'
                '</div>'
                '<div class="price-comparator__sep"></div>'
                '<div class="price-comparator__best">'
                '<span class="price-comparator__label">Meilleur prix</span>'
                f'<span class="price-comparator__value price-comparator__value--accent">{best_val:.0f}€</span>'
                '</div>'
                f'<span class="price-comparator__source">{escape(best_name)}</span>'
                '</div>'
            )
        return ''

    html = '<section class="article__retailers"><h2>Où <span>acheter</span></h2>'
    html += price_comparator_html()

    if retail:
        shown3 = retail[:3]
        extra = retail[3:]
        html += '<div class="retailers-section"><h3 class="retailers-section__title">Retail</h3>'
        html += '<div class="retailers-list">'
        for rt3 in shown3:
            html += make_row(rt3)
        html += '</div>'
        if extra:
            html += '<div class="retailers-accordion" style="display:none;"><div class="retailers-list">'
            for rte in extra:
                html += make_row(rte)
            html += '</div></div>'
            nb = len(extra)
            btn = ('<button class="retailers-voir-tout" '
                   'onclick="var a=this.previousElementSibling;'
                   'a.style.display=a.style.display===&quot;none&quot;?&quot;block&quot;:&quot;none&quot;;">'
                   '+ ' + str(nb) + ' voir tout</button>')
            html += btn
        html += '</div>'

    if raffles:
        html += '<div class="retailers-section"><h3 class="retailers-section__title">🎰 Raffles</h3><div class="retailers-list">'
        html += "".join(make_row(rt) for rt in raffles)
        html += '</div></div>'

    if resell:
        html += '<div class="retailers-section"><h3 class="retailers-section__title">📈 Resell</h3><div class="retailers-list">'
        html += "".join(make_row(rt) for rt in resell)
        html += '</div></div>'

    html += '</section>'
    return html


def primary_buy_button(r: dict) -> str:
    rets = get_retailers_for_release(r)
    retail = next((x for x in rets if not x.get("resell") and not x.get("type") == "resell"), None)
    target = retail or (rets[0] if rets else None)
    url = (target and target.get("url")) or r.get("buy_url")
    if not url:
        return ""
    label = "Voir sur WhenToCop" if "whentocop" in url else "Acheter maintenant"
    # Appliquer Awin si disponible et pas resell
    is_resell = target and (target.get("resell") or target.get("type") == "resell")
    if not is_resell and "whentocop" not in url:
        awin_url = build_awin_url(url)
        if awin_url:
            url = awin_url
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
  <meta property="og:title" content="{title_attr} — SneakerDrop FR" />
  <meta property="og:description" content="{og_desc}" />
  <meta property="og:image" content="{og_image}" />
  <meta property="og:url" content="{canonical}" />
  <meta property="og:type" content="article" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{title_attr} — SneakerDrop FR" />
  <meta name="twitter:description" content="{og_desc}" />
  <meta name="twitter:image" content="{og_image}" />
  <script type="application/ld+json">{jsonld}</script>
  <link rel="icon" href="/favicon.ico" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;600;700;900&family=Barlow+Condensed:wght@400;600;700;900&family=Bebas+Neue&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/assets/css/shared.css" />
  <script src="/assets/js/common.js"></script>
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
    .article__colorway{{font-family:var(--font-cond);color:var(--muted);font-size:.95rem;margin-bottom:.4rem;letter-spacing:.03em}}
    .article__sku{{font-family:var(--font-cond);color:var(--muted);font-size:.8rem;margin-bottom:1rem;letter-spacing:.04em}}
    .article__sku-label{{font-weight:900;color:var(--black);text-transform:uppercase;margin-right:.35rem}}
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
    .retailers-section{{margin-bottom:1.25rem}}
    .retailers-section__title{{font-family:var(--font-cond);font-size:.85rem;font-weight:900;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:.6rem;padding-bottom:.4rem;border-bottom:1px solid var(--border)}}
    .retailers-list{{display:flex;flex-direction:column;gap:.6rem}}
    .retailer{{display:flex;align-items:center;gap:1rem;padding:.95rem 1.2rem;background:#fff;border:1px solid var(--border);border-radius:10px;transition:border-color .15s,transform .15s,box-shadow .15s}}
    .retailer:hover{{border-color:var(--black);transform:translateY(-1px);box-shadow:var(--shadow)}}
    .retailer__name{{font-family:var(--font-cond);font-weight:900;font-size:1rem;letter-spacing:.04em;text-transform:uppercase;flex:1}}
    .retailer__price{{font-family:var(--font-cond);font-weight:700;font-size:.95rem;color:var(--black)}}
    .retailer__badge{{font-family:var(--font-cond);font-size:.7rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;padding:.2rem .55rem;border-radius:999px}}
    .retailer__badge--retail{{background:#E6F4EA;color:#137333}}
    .retailer__badge--resell{{background:#FCE8E6;color:#A50E0E}}
    .retailer__badge--raffle{{background:#FFF3CD;color:#856404}}
    .retailer__arrow{{font-family:var(--font-cond);font-weight:900;color:var(--muted)}}
    .retailers-voir-tout{{font-family:var(--font-cond);font-size:.7rem;font-weight:900;letter-spacing:.05em;text-transform:uppercase;padding:.4rem .9rem;border:1.5px dashed #ccc;border-radius:4px;background:none;color:#888;cursor:pointer;margin-top:.5rem;display:inline-block;}}
    .retailers-voir-tout:hover{{border-color:#000;color:#000;}}
    .retailers-accordion{{margin-top:.3rem;}}
    .price-comparator{{background:linear-gradient(135deg,#0A0A0A 0%,#1a1a1a 100%);border-radius:12px;padding:1.1rem 1.4rem;margin-bottom:1.25rem;display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap}}
    .price-comparator__best{{display:flex;flex-direction:column}}
    .price-comparator__label{{font-family:var(--font-cond);font-size:.65rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:rgba(255,255,255,.5);margin-bottom:.15rem}}
    .price-comparator__value{{font-family:var(--font-display);font-size:1.6rem;color:#fff;line-height:1}}
    .price-comparator__value--accent{{color:var(--accent)}}
    .price-comparator__sep{{width:1px;height:36px;background:rgba(255,255,255,.15);flex-shrink:0}}
    .price-comparator__saving{{display:inline-flex;align-items:center;gap:.35rem;background:#E6F4EA;color:#137333;font-family:var(--font-cond);font-size:.8rem;font-weight:900;letter-spacing:.05em;text-transform:uppercase;padding:.3rem .75rem;border-radius:999px}}
    .price-comparator__source{{font-family:var(--font-cond);font-size:.75rem;color:rgba(255,255,255,.45);margin-left:auto}}
    .related{{margin-bottom:2.5rem}}
    .related h2{{font-family:var(--font-display);font-size:1.6rem;text-transform:uppercase;letter-spacing:.03em;margin-bottom:1rem}}
    .related h2 span{{color:var(--accent)}}
    .related-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem}}
    @media(max-width:600px){{.related-grid{{grid-template-columns:repeat(2,1fr)}}}}
    .related-card{{display:flex;flex-direction:column;background:#0A0A0A;border:1px solid rgba(255,255,255,.08);border-radius:10px;overflow:hidden;transition:border-color .2s,transform .2s;text-decoration:none}}
    .related-card:hover{{border-color:rgba(255,255,255,.3);transform:translateY(-3px)}}
    .related-card__img{{aspect-ratio:1;background:#fff;overflow:hidden;display:flex;align-items:center;justify-content:center;padding:.5rem}}
    .related-card__img img{{width:100%;height:100%;object-fit:contain}}
    .related-card__body{{padding:.65rem .75rem}}
    .related-card__brand{{font-family:var(--font-cond);font-size:.62rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:rgba(255,255,255,.4)}}
    .related-card__title{{font-family:var(--font-cond);font-size:.8rem;font-weight:900;text-transform:uppercase;color:#fff;line-height:1.2;margin:.2rem 0}}
    .related-card__price{{font-family:var(--font-cond);font-size:.85rem;font-weight:700;color:var(--accent)}}
    .restocks-section{{margin-bottom:2.5rem}}
    .restocks-section h2{{font-family:var(--font-display);font-size:1.6rem;text-transform:uppercase;letter-spacing:.03em;margin-bottom:1rem}}
    .restocks-section h2 span{{color:var(--accent)}}
    .restocks-list{{display:flex;flex-direction:column;gap:.75rem}}
    .restock-item{{background:var(--bg-alt);border:1px solid var(--border);border-radius:12px;padding:1rem 1.2rem;display:flex;align-items:flex-start;gap:1.2rem;flex-wrap:wrap}}
    .restock-item__date{{font-family:var(--font-cond);font-size:.78rem;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);min-width:110px;padding-top:.15rem}}
    .restock-item__retailers{{display:flex;flex-wrap:wrap;gap:.5rem;flex:1}}
    .restock-item__retailer{{display:inline-flex;align-items:center;gap:.4rem;background:#fff;border:1px solid var(--border);border-radius:8px;padding:.4rem .85rem;font-family:var(--font-cond);font-size:.85rem;font-weight:900;letter-spacing:.04em;text-transform:uppercase;color:var(--black);transition:border-color .15s,transform .15s}}
    .restock-item__retailer:hover{{border-color:var(--black);transform:translateY(-1px)}}
    .restock-item__retailer--nolink{{cursor:default}}
    .restock-item__retailer--nolink:hover{{transform:none;border-color:var(--border)}}
    .restock-item__price{{font-weight:700;color:var(--accent);margin-left:.2rem}}
    .restock-item__arrow{{color:var(--muted);font-size:.8rem}}
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
        <a href="/restocks.html" class="hbtn hbtn--solid hbtn--hide-sm">Restocks</a>
        <a href="https://t.me/SneakersDropsFR" target="_blank" rel="noopener" class="hbtn hbtn--tg">Telegram</a>
      </nav>
    </div>
  </header>

  <nav aria-label="Fil d'Ariane" style="background:#f5f5f5;padding:.6rem 1.5rem;font-size:.8rem;color:var(--muted)">
    <ol style="display:flex;list-style:none;gap:.5rem;align-items:center;max-width:1100px;margin:0 auto">
      <li><a href="/" style="color:var(--muted);text-decoration:none">Accueil</a></li>
      <li style="color:var(--border)">›</li>
      <li><a href="/sorties.html" style="color:var(--muted);text-decoration:none">Sorties</a></li>
      <li style="color:var(--border)">›</li>
      <li style="color:var(--text)">{title_html}</li>
    </ol>
  </nav>
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
          {sku_html}
          <div class="article__infos">
            <div class="article__info-row">
              <span class="article__info-label">Date</span>
              <span class="article__info-value">{date_value}</span>
            </div>
            <div class="article__info-row">
              <span class="article__info-label">Prix</span>
              <span class="article__info-value">{price_html}</span>
            </div>
            {silhouette_row}
            {year_row}
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
      {past_banner}
    {restocks_block}

      {related_block}

      <section class="article__faq" style="margin:2.5rem 0">
        <h2 style="font-family:var(--font-display);font-size:1.8rem;text-transform:uppercase;margin-bottom:1.5rem">Questions fréquentes</h2>
        <div style="border:1px solid var(--border);border-radius:12px;overflow:hidden">
          <div style="padding:1.25rem 1.5rem;border-bottom:1px solid var(--border)">
            <h3 style="font-size:1rem;font-weight:700;margin-bottom:.5rem">Quand sort la {title_html} ?</h3>
            <p style="color:var(--muted);font-size:.9rem">La {title_html} est officiellement prévue pour le {date_value} au prix retail de {price_html}.</p>
          </div>
          <div style="padding:1.25rem 1.5rem;border-bottom:1px solid var(--border)">
            <h3 style="font-size:1rem;font-weight:700;margin-bottom:.5rem">Où acheter la {title_html} en France ?</h3>
            <p style="color:var(--muted);font-size:.9rem">Retrouvez cette paire chez les retailers officiels listés ci-dessus (BSTN, Nike SNKRS, Footshop, etc.) le jour du drop, ou via leurs systèmes de raffles.</p>
          </div>
          <div style="padding:1.25rem 1.5rem">
            <h3 style="font-size:1rem;font-weight:700;margin-bottom:.5rem">Quel est le SKU de la {title_html} ?</h3>
            <p style="color:var(--muted);font-size:.9rem">Le code produit officiel (SKU) de cette paire est <strong>{sku_value}</strong>. Ce code permet de l'identifier précisément chez tous les retailers.</p>
          </div>
        </div>
      </section>
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
  <script>
  (function(){{
    var TRACKER = 'https://track.sneakerdropfr.fr/click';
    var RELEASE_ID = '{release_id}';
    function send(el){{
      try{{
        var isResell = el.classList.contains('retailer') &&
                       el.querySelector('.retailer__badge--resell') !== null;
        var isRaffle = el.classList.contains('retailer') &&
                       el.querySelector('.retailer__badge--raffle') !== null;
        var retailer = el.querySelector('.retailer__name');
        fetch(TRACKER, {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{
            release_id: RELEASE_ID,
            retailer:   retailer ? retailer.textContent.trim() : 'unknown',
            url:        el.href,
            is_resell:  isResell,
            is_raffle:  isRaffle
          }}),
          keepalive: true
        }}).catch(function(){{}});
      }}catch(e){{}}
    }}
    document.addEventListener('click', function(e){{
      var el = e.target.closest('a.retailer, a.article__buy');
      if(!el) return;
      if(el.classList.contains('article__buy')){{
        fetch(TRACKER, {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{
            release_id: RELEASE_ID,
            retailer:   'buy_btn',
            url:        el.href,
            is_resell:  false,
            is_raffle:  false
          }}),
          keepalive: true
        }}).catch(function(){{}});
      }} else {{
        send(el);
      }}
    }});
  }})();
  </script>
  <script>
    (function(){{
      try {{
        fetch('https://track.sneakerdropfr.fr/pageview', {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{page: window.location.pathname}}),
          keepalive: true
        }}).catch(function(){{}});
      }} catch(e) {{}}
    }})();
  </script>
</body>
</html>
"""


def restocks_html(r: dict) -> str:
    """Section Restocks — affiche l'historique des restocks si disponibles.
    Format attendu :
      restocks: [{date, retailers: [{name, url, price}]}, ...]
    """
    restocks = r.get("restocks") or []
    if not restocks:
        return ""

    FR_MONTHS_SHORT = ["jan","fév","mar","avr","mai","juin",
                       "juil","août","sep","oct","nov","déc"]

    def fmt_date(d: str) -> str:
        try:
            from datetime import datetime as _dt
            dt = _dt.fromisoformat(d[:10])
            return f"{dt.day} {FR_MONTHS_SHORT[dt.month-1]} {dt.year}"
        except Exception:
            return d or "Date inconnue"

    sorted_restocks = sorted(restocks, key=lambda rs: rs.get("date","") or "0000", reverse=True)

    items = []
    for rs in sorted_restocks:
        date_str = fmt_date(rs.get("date", ""))
        retailers_rs = rs.get("retailers") or []

        links = []
        for rt in retailers_rs:
            name = escape(rt.get("name", "Retailer"))
            url = rt.get("url", "")
            price = rt.get("price", "")
            if url:
                awin = build_awin_url(url)
                if awin:
                    url = awin
            price_html = (
                f'<span class="restock-item__price">{escape(str(price))}</span>'
                if price else ""
            )
            if url:
                links.append(
                    f'<a class="restock-item__retailer" href="{escape(url, quote=True)}" '
                    f'target="_blank" rel="noopener nofollow sponsored">'
                    f'{name}{price_html}'
                    f'<span class="restock-item__arrow">→</span></a>'
                )
            else:
                links.append(
                    f'<span class="restock-item__retailer restock-item__retailer--nolink">'
                    f'{name}{price_html}</span>'
                )

        if not links:
            continue

        items.append(
            f'<div class="restock-item">'
            f'<div class="restock-item__date">{date_str}</div>'
            f'<div class="restock-item__retailers">{"".join(links)}</div>'
            f'</div>'
        )

    if not items:
        return ""

    return (
        f'<section class="restocks-section">'
        f'<h2>Historique <span>restocks</span></h2>'
        f'<div class="restocks-list">{"".join(items)}</div>'
        f'</section>'
    )

def past_banner_html(r: dict) -> str:
    """Bandeau 'epuisee' pour les paires de releases_past.json."""
    if not r.get("past"):
        return ""
    title = escape(r.get("title", "").strip())
    silhouette = escape((r.get("silhouette") or r.get("brand") or "").strip())
    return (
        f'<div style="background:#1a1a1a;border:1px solid var(--border);border-radius:12px;'
        f'padding:1.25rem 1.5rem;margin-bottom:1.5rem;display:flex;align-items:center;gap:.75rem">'
        f'<span style="font-size:1.3rem">\U0001F6AB</span>'
        f'<div><strong style="color:#fff">Cette paire est epuisee.</strong> '
        f'<span style="color:var(--muted)">Decouvrez les prochaines sorties {silhouette} ci-dessous.</span></div>'
        f'</div>'
    )


def related_html(r: dict, all_releases: list) -> str:
    """Section Voir aussi — utilise similar_products en priorite, sinon meme marque."""
    brand = (r.get("brand") or "").strip()
    current_id = r.get("id", "")
    releases_index = {x["id"]: x for x in all_releases if x.get("id")}

    picks = []

    # 1. Utiliser similar_products si disponible
    similar_ids = r.get("similar_products") or []
    for sid in similar_ids:
        p = releases_index.get(sid)
        if p and p.get("image_url") and p.get("id") != current_id:
            picks.append(p)
        if len(picks) >= 4:
            break

    # 2. Fallback : meme marque si pas assez de similar
    EXCLUDE_KW = ["golf", " gs)", "(gs)", " td)", "(td)", " ps)", "(ps)",
                  " bp)", "(bp)", "infant", "toddler", "preschool", "kids",
                  "grade school", "cleat", "spike"]
    if len(picks) < 3 and brand:
        same_brand = [
            x for x in all_releases
            if x.get("brand","").strip() == brand
            and x.get("id") != current_id
            and x.get("id") not in [p["id"] for p in picks]
            and x.get("image_url")
            and not any(kw in x.get("title","").lower() for kw in EXCLUDE_KW)
        ]
        same_brand.sort(key=lambda x: (x.get("date","TBD") == "TBD", x.get("date","TBD")))
        picks += same_brand[:4 - len(picks)]

    if not picks:
        return ""

    picks = picks[:4]

    if not picks:
        return ""

    cards = []
    for p in picks:
        pid = p["id"]
        ptitle = escape(p.get("title",""))
        pbrand = escape(p.get("brand",""))
        pprice = escape(format_price(p.get("price")))
        pimg = escape(p.get("image_url",""), quote=True)
        cards.append(
            f'<a href="/sorties/{pid}.html" class="related-card">'
            f'<div class="related-card__img"><img src="{pimg}" alt="{ptitle}" loading="lazy"></div>'
            f'<div class="related-card__body">'
            f'<div class="related-card__brand">{pbrand}</div>'
            f'<div class="related-card__title">{ptitle}</div>'
            f'<div class="related-card__price">{pprice}</div>'
            f'</div></a>'
        )

    brand_html = escape(brand)
    return (
        f'<section class="related">'
        f'<h2>Paires <span>similaires</span></h2>'
        f'<div class="related-grid">{"".join(cards)}</div>'
        f'</section>'
    )


def render_page(r: dict, all_releases: list | None = None) -> str:
    rid = r.get("id", "")
    title = r.get("title", "").strip() or rid
    brand = (r.get("brand") or "").strip()
    cw = (r.get("colorway") or "").strip()
    date_fr = format_date_fr(r.get("date"))
    price = format_price(r.get("price"))
    image_url = (r.get("image_url") or "").strip()
    canonical = f"{SITE_BASE}/sorties/{rid}.html"

    title_html = escape(title, quote=False)
    title_attr = escape(title, quote=True)
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

    sku = (r.get("sku") or "").strip()
    sku_html = (
        f'<p class="article__sku"><span class="article__sku-label">SKU</span> {escape(sku)}</p>' if sku else ""
    )

    # release_window — affiché quand date == TBD
    release_window = (r.get("release_window") or "").strip()
    # Silhouette + year pour les info-rows
    silhouette = (r.get("silhouette") or "").strip()
    year = r.get("year")

    if image_url:
        img_tag = (
            '<img src="' + escape(image_url, quote=True) + '" '
            f'alt="{title_attr}" class="article__img" loading="lazy" '
            'onerror="this.src=\'/assets/images/placeholder.svg\';this.style.opacity=\'0.5\'">'
        )
    else:
        img_tag = '<img src="/placeholder.svg" alt="Visuel officiel à venir" style="width:100%;max-width:400px;opacity:.6">'

    # Meta title optimise < 60 chars
    suffix = " | SneakerDrop FR"
    date_fr_t = format_date_fr(r.get("date"))
    if date_fr_t and date_fr_t != "TBD":
        prefix = "Date de sortie " + title
    else:
        prefix = title
    max_base = 60 - len(suffix)
    if len(prefix) > max_base:
        # Priorite 1 : retirer "Date de sortie " plutot que couper le nom du produit
        if prefix.startswith("Date de sortie ") and len(title) <= max_base:
            prefix = title
        elif len(title) > max_base:
            # Le titre seul est trop long : on le garde entier (Google tronquera proprement avec ...)
            prefix = title
        # sinon : prefix reste tel quel (legerement > 60 chars, accepte)
    meta_title = escape(prefix + suffix, quote=False)

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
    elif r.get("restocks"):
        # Fallback : utiliser les retailers du restock le plus recent
        sorted_restocks = sorted(r["restocks"], key=lambda rs: rs.get("date","") or "0000", reverse=True)
        if sorted_restocks:
            latest_rets = sorted_restocks[0].get("retailers") or []
            offer_list = []
            for ret in latest_rets:
                url = ret.get("url")
                if not url:
                    continue
                offer = {
                    "@type": "Offer",
                    "url": url,
                    "seller": {"@type": "Organization", "name": ret.get("name", "Retailer")},
                    "availability": "https://schema.org/InStock",
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
        title_attr=title_attr,
        meta_desc=meta_desc,
        canonical=escape(canonical, quote=True),
        og_desc=og_desc,
        og_image=og_image,
        jsonld=jsonld,
        img_tag=img_tag,
        brand_html=brand_html,
        colorway_html=colorway_html,
        sku_html=sku_html,
        sku_value=escape(sku) if sku else 'N/A',
        date_value=escape(release_window if date_fr == "TBD" and release_window else date_fr),
        silhouette_row=(
            f'<div class="article__info-row">'
            f'<span class="article__info-label">Silhouette</span>'
            f'<span class="article__info-value">{escape(silhouette)}</span>'
            f'</div>' if silhouette else ''
        ),
        year_row=(
            f'<div class="article__info-row">'
            f'<span class="article__info-label">Année</span>'
            f'<span class="article__info-value">{escape(str(year))}</span>'
            f'</div>' if year else ''
        ),
        price_html=price_html,
        buy_btn=primary_buy_button(r),
        editorial=editorial_text(r),
        retailers_block=retailers_html(r),
        restocks_block=restocks_html(r),
        past_banner=past_banner_html(r),
        related_block=related_html(r, all_releases or []),
        release_id=escape(rid),
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

    # Charger releases_past.json pour enrichir all_releases (similar_products)
    past_releases = []
    if os.path.exists(RELEASES_PAST_PATH):
        try:
            with open(RELEASES_PAST_PATH, "r", encoding="utf-8") as f:
                past_releases = json.load(f)
        except Exception:
            past_releases = []
    all_releases = releases + past_releases

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
        html = render_page(r, all_releases)
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
