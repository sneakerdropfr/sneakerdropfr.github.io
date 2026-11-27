#!/usr/bin/env python3
"""Liens HTML internes pour le référencement (lancé au déploiement GitHub Pages, avant la construction).

- Ajoute un bloc de vrais liens vers les fiches /sorties/ dans index.html, sorties.html et categories/*.html
  (entre <!-- SEO-LINKS:START --> et <!-- SEO-LINKS:END -->, remplacé à chaque passage).
- Crée toutes-les-sorties.html : calendrier complet, sorties à venir puis passées, avec un lien vers chaque fiche.
- Ajoute toutes-les-sorties.html au sitemap.xml s'il n'y est pas.
Ne touche qu'aux fichiers du dossier de travail du déploiement : rien n'est commité.
"""
import json, os, re, sys
from datetime import date
from html import escape

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
SITE = "https://sneakerdropfr.fr"
ARCHIVE = "toutes-les-sorties.html"
COURT = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
START, END = "<!-- SEO-LINKS:START -->", "<!-- SEO-LINKS:END -->"
JORDAN = {"air jordan", "jordan", "jordan brand"}
CATS = {
    "nike": lambda e: brand(e) == "nike" and not is_jordan(e),
    "jordan": lambda e: is_jordan(e),
    "adidas": lambda e: brand(e) == "adidas",
    "new-balance": lambda e: brand(e) == "new balance",
}
CAT_NAMES = {"nike": "Nike", "jordan": "Jordan", "adidas": "Adidas", "new-balance": "New Balance"}


def brand(e): return (e.get("brand") or "").strip().lower()
def is_jordan(e): return brand(e) in JORDAN or (e.get("title") or "").lower().startswith("air jordan")


def load(fn):
    p = os.path.join(ROOT, fn)
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return []


def clean_title(t):
    return re.sub(r"\s+", " ", (t or "").replace("\xa0", " ")).strip()


def collect():
    today = date.today().isoformat()
    seen, up, past = set(), [], []
    for e in load("releases.json") + load("releases_past.json"):
        i = e.get("id") or ""
        if not i or i in seen or not re.fullmatch(r"[A-Za-z0-9._-]+", i):
            continue
        if not os.path.exists(os.path.join(ROOT, "sorties", i + ".html")):
            continue
        seen.add(i)
        d = e.get("date") or "TBD"
        (up if d == "TBD" or d >= today else past).append(e)
    up.sort(key=lambda e: (e.get("date") in (None, "", "TBD"), e.get("date") or ""))
    past.sort(key=lambda e: e.get("date") or "", reverse=True)
    return up, past


def month_label(d):
    m = re.match(r"(\d{4})-(\d{2})", d or "")
    return f"{MOIS[int(m.group(2)) - 1].capitalize()} {m.group(1)}" if m else "Date à confirmer"


def day_label(d):
    m = re.match(r"\d{4}-(\d{2})-(\d{2})", d or "")
    return f"{int(m.group(2))} {COURT[int(m.group(1)) - 1]}" if m else "TBD"


def li(e):
    return (f'<li><a href="/sorties/{e["id"]}.html">{escape(clean_title(e.get("title")) or e["id"])}</a>'
            f' <span class="seo-d">{day_label(e.get("date"))}</span></li>')


def grouped(items):
    out, cur = [], None
    for e in items:
        m = month_label(e.get("date"))
        if m != cur:
            if cur is not None:
                out.append("</ul>")
            out.append(f"<h3>{m}</h3><ul>")
            cur = m
        out.append(li(e))
    if cur is not None:
        out.append("</ul>")
    return "".join(out)


CSS = ("<style>.seo-links{max-width:1200px;margin:2.5rem auto;padding:0 1rem;font-family:var(--font-body,'Barlow',sans-serif)}"
       ".seo-links h2{font-family:var(--font-display,'Bebas Neue',sans-serif);font-size:1.6rem;letter-spacing:.03em;margin:0 0 .8rem;color:var(--text,#0A0A0A)}"
       ".seo-links h2 span{color:var(--accent,#FF2D2D)}"
       ".seo-links h3{font-family:var(--font-cond,'Barlow Condensed',sans-serif);font-size:.95rem;text-transform:uppercase;letter-spacing:.06em;margin:1.2rem 0 .4rem;color:var(--muted,#666)}"
       ".seo-links ul{list-style:none;margin:0;padding:0;columns:3 260px;column-gap:2rem}"
       ".seo-links li{break-inside:avoid;padding:.18rem 0;font-size:.9rem;line-height:1.35}"
       ".seo-links a{color:var(--text,#0A0A0A);text-decoration:none}.seo-links a:hover{color:var(--accent,#FF2D2D);text-decoration:underline}"
       ".seo-links .seo-d{color:var(--muted,#888);font-size:.8rem;white-space:nowrap}"
       ".seo-links .seo-all{display:inline-block;margin-top:1rem;font-family:var(--font-cond,'Barlow Condensed',sans-serif);font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--accent,#FF2D2D)}</style>")


def block(title_html, body):
    return (f'{START}\n{CSS}<section class="seo-links" aria-label="Liste des sorties">'
            f'<h2>{title_html}</h2>{body}'
            f'<a class="seo-all" href="/{ARCHIVE}">Voir toutes les sorties →</a></section>\n{END}')


def inject(path, html_block, anchors):
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        print(f"  {path} absent, ignoré"); return
    s = open(p, encoding="utf-8").read()
    s = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", s, flags=re.S)
    for a in anchors:
        if a in s:
            s = s.replace(a, html_block + "\n" + a, 1)
            open(p, "w", encoding="utf-8").write(s)
            print(f"  {path} : liens ajoutés")
            return
    print(f"  {path} : ancre introuvable, ignoré")


def archive_page(up, past):
    n = len(up) + len(past)
    desc = (f"Calendrier complet des sorties sneakers en France : {len(up)} sorties à venir et "
            f"{len(past)} sorties passées (Nike, Jordan, Adidas, New Balance...), avec dates, prix et liens retailers.")
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Toutes les sorties sneakers — calendrier complet | SneakerDropFR</title>
<meta name="description" content="{escape(desc, quote=True)}">
<link rel="canonical" href="{SITE}/{ARCHIVE}">
<meta property="og:title" content="Toutes les sorties sneakers | SneakerDropFR">
<meta property="og:description" content="{escape(desc, quote=True)}">
<meta property="og:url" content="{SITE}/{ARCHIVE}">
<meta property="og:type" content="website">
<link rel="icon" href="/favicon.ico">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:wght@400;600&family=Barlow+Condensed:wght@600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#FFFFFF;--text:#0A0A0A;--accent:#FF2D2D;--muted:#666;--border:#E5E5E5;--bg-alt:#F5F5F5;
--font-display:'Bebas Neue',sans-serif;--font-body:'Barlow',sans-serif;--font-cond:'Barlow Condensed',sans-serif}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:var(--font-body)}}
header{{border-bottom:1px solid var(--border);padding:1rem}}
header .in{{max-width:1200px;margin:0 auto;display:flex;gap:1.5rem;align-items:center;flex-wrap:wrap}}
header a{{color:var(--text);text-decoration:none;font-family:var(--font-cond);font-weight:700;text-transform:uppercase;letter-spacing:.05em;font-size:.9rem}}
header .logo{{font-family:var(--font-display);font-size:1.6rem;letter-spacing:.03em}}
header .logo span{{color:var(--accent)}}
h1{{font-family:var(--font-display);font-size:2.6rem;letter-spacing:.03em;max-width:1200px;margin:2rem auto .3rem;padding:0 1rem}}
h1 span{{color:var(--accent)}}
.intro{{max-width:1200px;margin:0 auto;padding:0 1rem;color:var(--muted)}}
footer{{text-align:center;padding:2rem;font-family:var(--font-cond);font-size:.8rem;color:var(--muted);border-top:1px solid var(--border);margin-top:3rem}}
footer a{{color:var(--muted)}}
</style>
</head>
<body>
<header><div class="in">
<a class="logo" href="/">SneakerDrop<span>FR</span></a>
<a href="/sorties.html">Sorties</a><a href="/restocks.html">Restocks</a><a href="/deals.html">Deals</a><a href="/raffles.html">Raffles</a>
<a href="/categories/nike.html">Nike</a><a href="/categories/jordan.html">Jordan</a><a href="/categories/adidas.html">Adidas</a><a href="/categories/new-balance.html">New Balance</a>
</div></header>
<h1>Toutes les <span>sorties</span> sneakers</h1>
<p class="intro">Le calendrier complet des sorties sneakers en France : Nike, Air Jordan, Adidas, New Balance, ASICS, Vans, Puma et bien d'autres. Chaque fiche donne la date de sortie, le prix retail et les liens vers les magasins officiels qui proposent la paire, sans revendeurs. On y retrouve {n} paires : les {len(up)} prochaines sorties, puis les {len(past)} sorties passées, mois par mois.</p>
{CSS}
<section class="seo-links"><h2>Sorties <span>à venir</span></h2>{grouped(up)}</section>
<section class="seo-links"><h2>Sorties <span>passées</span></h2>{grouped(past)}</section>
<footer>© {date.today().year} SneakerDrop FR — <a href="/">Accueil</a> · <a href="/mentions-legales.html">Mentions légales</a> · <a href="/privacy.html">Confidentialité</a></footer>
</body>
</html>
"""


def add_to_sitemap():
    p = os.path.join(ROOT, "sitemap.xml")
    if not os.path.exists(p):
        return
    s = open(p, encoding="utf-8").read()
    url = f"{SITE}/{ARCHIVE}"
    if url in s or "</urlset>" not in s:
        return
    entry = (f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{date.today().isoformat()}</lastmod>\n"
             f"    <changefreq>daily</changefreq>\n    <priority>0.8</priority>\n  </url>\n")
    open(p, "w", encoding="utf-8").write(s.replace("</urlset>", entry + "</urlset>", 1))
    print("  sitemap.xml : toutes-les-sorties.html ajoutée")


SKIP_DIRS = {".git", "_site", "tests", "node_modules", "assets", "__pycache__", "scripts", ".github"}


def add_nav_links():
    """Lien « Toutes les sorties » dans le menu (header__nav) et le pied de page de chaque page HTML.
    Dossier de travail seulement, au déploiement : rien n'est commité, les fiches ne sont pas régénérées."""
    nav_n = foot_n = 0
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for f in fns:
            if not f.endswith(".html") or f == ARCHIVE:
                continue
            path = os.path.join(dp, f)
            try:
                s = open(path, encoding="utf-8").read()
            except Exception:
                continue
            o = s
            m = re.search(r'<nav class="header__nav">(.*?)</nav>', s, re.S)
            if m and ">BSTN Deals</a>" in m.group(1):
                s = s[:m.start(1)] + m.group(1).replace(">BSTN Deals</a>", ">Sneakers Deals</a>") + s[m.end(1):]
                m = re.search(r'<nav class="header__nav">(.*?)</nav>', s, re.S)
            if m and ARCHIVE not in m.group(1):
                a = re.search(r'<a href="/?sorties\.html"([^>]*)>[^<]*</a>', m.group(1))
                if a:
                    attrs = a.group(1)
                    if "hbtn--keep" in attrs and ".hbtn--desktop" in s and "hbtn--desktop" not in attrs:
                        attrs = attrs.replace("hbtn--keep", "hbtn--keep hbtn--desktop", 1)
                    link = f'\n        <a href="/{ARCHIVE}"{attrs}>Toutes les sorties</a>'
                    pos = m.start(1) + a.end()
                    s = s[:pos] + link + s[pos:]
                    nav_n += 1
            fm = re.search(r'<footer\b.*?</footer>', s, re.S)
            if fm and ARCHIVE not in fm.group(0):
                sm = re.search(r'<a href="/?sitemap\.xml"([^>]*)>Sitemap</a>', fm.group(0))
                if sm:
                    pos = fm.start() + sm.end()
                    s = s[:pos] + f' — <a href="/{ARCHIVE}"{sm.group(1)}>Toutes les sorties</a>' + s[pos:]
                else:
                    pos = fm.end() - len("</footer>")
                    s = s[:pos] + (f'<div style="text-align:center;font-size:.75rem;margin:.5rem 0">'
                                   f'<a href="/{ARCHIVE}" style="color:inherit">Toutes les sorties</a></div>\n  ') + s[pos:]
                foot_n += 1
            if s != o:
                open(path, "w", encoding="utf-8").write(s)
    print(f"  lien Toutes les sorties : menu {nav_n} page(s), pied de page {foot_n} page(s)")


def _num(v):
    """Prix numérique en texte (150, 91.99), ou None."""
    if isinstance(v, (int, float)) and v > 0:
        return ("%.2f" % v).rstrip("0").rstrip(".")
    if isinstance(v, str):
        t = re.sub(r"[^\d.,]", "", v).replace(",", ".")
        try:
            return _num(float(t)) if t else None
        except ValueError:
            return None
    return None


def fix_product_offers():
    """JSON-LD Product des fiches : champ offers toujours présent, avec prix retail et disponibilité.
    Dossier de travail seulement, au déploiement : rien n'est commité, les fiches ne sont pas régénérées."""
    idx = {}
    for fn_, is_past in (("releases_past.json", True), ("releases.json", False)):
        d = load(fn_)
        d = d if isinstance(d, list) else (d.get("releases") or [])
        for e in d:
            if e.get("id"):
                idx[e["id"]] = (is_past, e)
    d_ = os.path.join(ROOT, "sorties")
    if not os.path.isdir(d_):
        return
    fixed = added = noprice = 0
    for f in os.listdir(d_):
        if not f.endswith(".html"):
            continue
        path = os.path.join(d_, f)
        try:
            s = open(path, encoding="utf-8").read()
        except Exception:
            continue
        m = re.search(r'(<script type="application/ld\+json">)(.*?)(</script>)', s, re.S)
        if not m:
            continue
        try:
            obj = json.loads(m.group(2))
        except Exception:
            continue
        if obj.get("@type") != "Product":
            continue
        is_past, e = idx.get(f[:-5], (None, {}))
        if is_past is None:
            is_past = bool(re.search(r"Cette paire est epuisee", s))
        if not is_past:
            avail = "https://schema.org/PreOrder"
        elif e.get("still_available") or "Cette paire est epuisee" not in s:
            avail = "https://schema.org/InStock"
        else:
            avail = "https://schema.org/OutOfStock"
        base = _num(e.get("price"))
        if not base:
            pm = re.search(r"au prix retail a (\d+(?:[.,]\d+)?) €", obj.get("description") or "")
            base = _num(pm.group(1)) if pm else None
        offers = obj.get("offers")
        if isinstance(offers, dict):
            offers = [offers]
        new = []
        for o in offers or []:
            o = dict(o)
            pr = _num(o.get("price")) or base
            if not pr:
                continue
            o["price"] = pr
            o["priceCurrency"] = o.get("priceCurrency") or "EUR"
            o["availability"] = avail
            o.setdefault("itemCondition", "https://schema.org/NewCondition")
            new.append(o)
        if not new and base:
            new = [{"@type": "Offer", "url": obj.get("url") or f"https://sneakerdropfr.fr/sorties/{f}",
                    "price": base, "priceCurrency": "EUR", "availability": avail,
                    "itemCondition": "https://schema.org/NewCondition"}]
            added += 1
        if not new:
            noprice += 1
            continue
        sku = (e.get("sku") or "").strip()
        if not sku:
            sm = re.search(r'<span class="article__sku-label">SKU</span> ([^<]+)</p>', s)
            sku = sm.group(1).strip() if sm else ""
        sku = sku.replace("&#x27;", "'").replace("&amp;", "&")
        before = json.dumps(obj, sort_keys=True)
        if sku and "," not in sku and len(sku) <= 40:
            obj.setdefault("sku", sku)
            obj.setdefault("mpn", sku)
        img = obj.get("image")
        if isinstance(img, str) and img.startswith("/"):
            obj["image"] = "https://sneakerdropfr.fr" + img
        obj["offers"] = new
        if json.dumps(obj, sort_keys=True) == before:
            continue
        js = json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")
        s = s[:m.start(2)] + js + s[m.end(2):]
        open(path, "w", encoding="utf-8").write(s)
        fixed += 1
    print(f"  JSON-LD offers : {fixed} fiche(s) corrigée(s), dont {added} sans retailer ; {noprice} sans prix connu")


# --- Liens affiliés : uniquement les tiens (Awin 2855487) ou des liens directs vers le magasin ---
MY_AWIN = "2855487"
# Programmes Awin acceptés : awinmid -> domaine du magasin. Ajouter ici chaque nouvelle acceptation.
AWIN_OK = {"104979": "bstn.com", "20964": "solebox.com", "122628": "snipes.com", "121522": "reebok"}
_TRACK = re.compile(r"^(utm_.*|cp|cjevent|cjdata|im_ref|irclickid|irgwc|awc|sv1|sv_.*|ranmid|raneaid|ransiteid|siteid|"
                    r"clickref|wgu|wgexpiry|sid|fbclid|gclid|_ga|mc_.*|irpid|sharedid|afsrc)$", re.I)
try:
    _MAP = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "direct_links.json"), encoding="utf-8"))
except Exception:
    _MAP = {}


def _strip(u):
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
    p = urlsplit(u)
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
         if not _TRACK.match(k) and not re.search(r"737541|whentocop", v, re.I) and not k.lower().startswith("ns_")]
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(q, safe=":/,"), p.fragment))


def _wrap(u):
    """Lien direct vers un magasin dont le programme Awin est accepté -> lien affilié à ton compte."""
    from urllib.parse import urlsplit, quote
    h = urlsplit(u).netloc.lower()
    for mid, dom in AWIN_OK.items():
        if dom in h:
            return f"https://www.awin1.com/cread.php?awinaffid={MY_AWIN}&awinmid={mid}&ued={quote(u, safe='')}"
    return u


def direct_url(u):
    if not isinstance(u, str) or not u.startswith("http"):
        return u
    from urllib.parse import urlsplit, parse_qs, unquote
    p = urlsplit(u); h = p.netloc.lower(); q = parse_qs(p.query)
    g = lambda k: (q.get(k) or [""])[0]
    t = None
    if "awin1.com" in h:
        if "cread.php" in p.path:
            aff, mid = g("awinaffid"), g("awinmid")
            if aff == MY_AWIN or mid in AWIN_OK:
                from urllib.parse import quote
                ued = g("ued")
                ued2 = _strip(ued) if ued and re.search(r"737541|whentocop", ued, re.I) else ued
                if aff == MY_AWIN and ued2 == ued:
                    return u
                t = f"https://www.awin1.com/cread.php?awinaffid={MY_AWIN}&awinmid={mid}"
                return t + (f"&ued={quote(ued2, safe='')}" if ued2 else "")
            t = g("ued") or g("p")
        elif "pclick.php" in p.path:
            if g("a") == MY_AWIN:
                return u
            t = _MAP.get(u)
            if not t:
                return u
    elif "link.whentocop.fr" in h:
        t = _MAP.get(u)
        if not t:
            return u
    elif re.search(r"(dpbolvw\.net|tkqlhce\.com|kqzyfj\.com|jdoqocy\.com|anrdoezrs\.net)$", h):
        t = g("url")
    elif "linksynergy.com" in h:
        t = g("murl")
    elif h.endswith("pxf.io") or h.endswith("sjv.io"):
        t = g("u")
    elif h == "prf.hn" or h.endswith(".prf.hn"):
        m = re.search(r"/destination:([^/?#]+)", p.path + ("?" + p.query if p.query else ""))
        t = unquote(m.group(1)) if m else None
    elif "ikhnaie" in h:
        t = g("wgtarget")
    if t:
        t = unquote(t) if t.startswith("http%3A") or t.startswith("https%3A") else t
        if not t.startswith("http"):
            return u
        return _wrap(_strip(t))
    if re.search(r"whentocop|wtc-tech|irpid=2379306|737541", u, re.I) and "whentocop" not in h:
        return _strip(u)
    return u


_URL_RE = re.compile(r"""(["'])(https?://(?:\\.|(?!\1)[^\\])*?)\1""")


def _fix_text(s):
    from html import unescape
    def rep(m):
        raw, tail = m.group(2), ""
        if len(raw) > 3000:
            return m.group(0)
        if "\n" in raw:
            raw, tail = raw.split("\n", 1)
            tail = "\n" + tail
        bs = "\\" in raw
        v = raw.replace('\\"', '"').replace("\\/", "/") if bs else raw
        v = unescape(v) if "&" in v else v
        w = direct_url(v)
        if w == v:
            return m.group(0)
        w = w.strip()
        if "&amp;" in raw or "&quot;" in raw or "&#" in raw:
            w = w.replace("&", "&amp;")
        if bs:
            w = w.replace('"', '\\"')
        return m.group(1) + w + tail + m.group(1)
    return _URL_RE.sub(rep, s)


def _fix_json(x):
    if isinstance(x, list):
        return [_fix_json(v) for v in x]
    if isinstance(x, dict):
        return {k: _fix_json(v) for k, v in x.items()}
    if isinstance(x, str) and x.startswith("http"):
        return direct_url(x)
    return x


def fix_affiliate_links():
    """Au déploiement : remplace les liens affiliés d'autres éditeurs (WhenToCop…) dans les JSON et les pages."""
    nj = nh = 0
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for f in fns:
            path = os.path.join(dp, f)
            if f.endswith(".json") and dp == ROOT:
                try:
                    data = json.load(open(path, encoding="utf-8"))
                except Exception:
                    continue
                new = _fix_json(data)
                if new != data:
                    json.dump(new, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2); nj += 1
            elif f.endswith(".html"):
                try:
                    s = open(path, encoding="utf-8").read()
                except Exception:
                    continue
                s2 = _fix_text(s)
                if s2 != s:
                    open(path, "w", encoding="utf-8").write(s2); nh += 1
    print(f"  liens affiliés convertis : {nj} JSON, {nh} page(s)")


DU_JS = 'var OK={"104979":1,"20964":1,"122628":1,"121522":1},ME="2855487";function du(u){try{var p=new URL(u),h=p.hostname,q=p.searchParams,t=null;if(/awin1\\.com$/.test(h)&&/cread/.test(p.pathname)){var a=q.get("awinaffid");if(a===ME)return u;if(OK[q.get("awinmid")]){q.set("awinaffid",ME);return p.toString()}t=q.get("ued")}else if(/(dpbolvw\\.net|tkqlhce\\.com|kqzyfj\\.com|jdoqocy\\.com|anrdoezrs\\.net)$/.test(h))t=q.get("url");else if(/linksynergy\\.com$/.test(h))t=q.get("murl");else if(/(pxf|sjv)\\.io$/.test(h))t=q.get("u");else if(/ikhnaie/.test(h))t=q.get("wgtarget");else if(/prf\\.hn$/.test(h)){var m=u.match(/destination:([^/?#]+)/);t=m?decodeURIComponent(m[1]):null}if(t&&t.indexOf("http")===0)u=t;else if(/awin1\\.com$/.test(h))return u;var r=new URL(u),ch=false;Array.from(r.searchParams.keys()).forEach(function(k){var v=r.searchParams.get(k)||"";if(/^(utm_|cjevent|cjdata|im_ref|irclickid|irpid|awc|sv1|sv_|ns_|clickref|sharedid|afsrc|wgu|wgexpiry)/i.test(k)||/737541|whentocop/i.test(v)){r.searchParams.delete(k);ch=true}});return ch?r.toString():u}catch(e){return u}}'

AFF_JS = ('<script id="aff-first">(function(){var A=["bstn","solebox","snipes"];'
          'function rk(r){var n=((r&&r.name)||"").toLowerCase().trim();for(var i=0;i<A.length;i++){if(n.indexOf(A[i])===0)return i}return 9}'
          'function fix(x,d){if(!x||typeof x!=="object"||d>6)return x;if(Array.isArray(x)){for(var i=0;i<x.length;i++)fix(x[i],d+1);return x}'
          'if(Array.isArray(x.retailers)&&x.retailers.length>1){x.retailers=x.retailers.map(function(r,i){return[r,i]})'
          '.sort(function(a,b){return rk(a[0])-rk(b[0])||a[1]-b[1]}).map(function(p){return p[0]})}'
          'for(var k in x){if(typeof x[k]==="string"&&x[k].indexOf("http")===0)x[k]=du(x[k]);else if(x[k]&&typeof x[k]==="object")fix(x[k],d+1)}return x}' + DU_JS +
          'var j=Response.prototype.json;Response.prototype.json=function(){return j.call(this).then(function(v){try{return fix(v,0)}catch(e){return v}})}})();</script>')


def add_affiliate_sort():
    """Pages qui affichent les sorties depuis les JSON : retailers affiliés (BSTN, Solebox, Snipes) en tête,
    quel que soit l'ordre des données. Dossier de travail seulement, au déploiement."""
    n = 0
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and d != "sorties"]
        for f in fns:
            if not f.endswith(".html"):
                continue
            path = os.path.join(dp, f)
            try:
                s = open(path, encoding="utf-8").read()
            except Exception:
                continue
            if 'id="aff-first"' in s or ".json()" not in s or "<head>" not in s:
                continue
            s = s.replace("<head>", "<head>\n" + AFF_JS, 1)
            open(path, "w", encoding="utf-8").write(s)
            n += 1
    print(f"  tri affiliés en tête : {n} page(s)")


def _incomplete(e):
    """Paire sans aucun magasin et sans date confirmée (ou à venir sans prix) : fiche vide, jamais affichée."""
    if not isinstance(e, dict) or not e.get("id") or e.get("retailers"):
        return False
    d = str(e.get("date") or "").strip()
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})$", d)
    if m:
        d = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    if not re.match(r"\d{4}-\d{2}-\d{2}$", d):
        return True
    return d >= date.today().isoformat() and not _num(e.get("price"))


def hide_incomplete():
    """Au déploiement (dossier de travail, sans commit) : retire des flux JSON, des fiches et du sitemap
    les paires vides (ex. anciennes entrées Sneaker News sans magasin ni date)."""
    blocked = set()
    try:
        blocked |= set(json.load(open(os.path.join(ROOT, "scripts", "fiches_masquees.json"), encoding="utf-8")))
    except Exception:
        pass

    def clean(x):
        if isinstance(x, list):
            out = []
            for v in x:
                if isinstance(v, dict) and v.get("id") and (_incomplete(v) or v["id"] in blocked):
                    blocked.add(v["id"]); continue
                out.append(clean(v))
            return out
        if isinstance(x, dict):
            return {k: clean(v) for k, v in x.items()}
        return x

    for fn in ("releases.json", "releases_past.json", "weekly_data.json", "bstn_upcoming.json"):
        p = os.path.join(ROOT, fn)
        if not os.path.exists(p):
            continue
        try:
            data = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        new = clean(data)
        if new != data:
            json.dump(new, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    n = 0
    for i in blocked:
        f = os.path.join(ROOT, "sorties", i + ".html")
        if os.path.exists(f):
            os.remove(f); n += 1
    sm = os.path.join(ROOT, "sitemap.xml")
    if os.path.exists(sm) and blocked:
        s = open(sm, encoding="utf-8").read()
        s2 = re.sub(r"\s*<url>\s*<loc>[^<]*/sorties/([^<]+)\.html</loc>.*?</url>",
                    lambda m: "" if m.group(1) in blocked else m.group(0), s, flags=re.S)
        if s2 != s:
            open(sm, "w", encoding="utf-8").write(s2)
    print(f"  paires incomplètes masquées : {len(blocked)} ({n} fiche(s) retirée(s))")


def main():
    hide_incomplete()
    fix_affiliate_links()
    up, past = collect()
    print(f"SEO links : {len(up)} à venir, {len(past)} passées (fiches existantes)")
    if not up and not past:
        print("  aucune fiche, rien à faire"); return
    open(os.path.join(ROOT, ARCHIVE), "w", encoding="utf-8").write(archive_page(up, past))
    print(f"  {ARCHIVE} : {len(up) + len(past)} liens")
    dated = [e for e in up if re.match(r"\d{4}-\d{2}-\d{2}$", e.get("date") or "")]
    home = block("Prochaines <span>sorties</span>", grouped(dated[:60]))
    inject("index.html", home, ['<footer class="footer">', "</body>"])
    inject("sorties.html", home, ['<footer class="footer">', "</body>"])
    for slug, f in CATS.items():
        cu = [e for e in dated if f(e)]
        cp = [e for e in past if f(e)][:80]
        body = ""
        if cu:
            body += grouped(cu)
        if cp:
            body += '<h2 style="margin-top:2rem">Dernières <span>sorties</span></h2>' + grouped(cp)
        if body:
            inject(f"categories/{slug}.html",
                   block(f"Sorties <span>{CAT_NAMES[slug]}</span>", body), ["<footer", "</body>"])
    add_to_sitemap()
    add_nav_links()
    fix_product_offers()
    add_affiliate_sort()


if __name__ == "__main__":
    main()
