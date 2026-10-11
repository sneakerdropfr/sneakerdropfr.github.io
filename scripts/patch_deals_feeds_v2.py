#!/usr/bin/env python3
"""deals_affilies.py : adaptation aux flux Snipes FR et Solebox EN.
- marque lue dans brand_name (noms Snipes sans marque) ; marque ajoutée au nom si absente
- modèles enfants en français écartés (Tout-Petits, etc.)
- tailles retirées des noms Solebox EN (Size …, Women/Men, Sneaker)
- doublons de tailles regroupés par image"""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "_feeds_v2" in s:
    print("Déjà patché."); sys.exit(0)
R = [
 ("            if not is_key_brand(nm): continue\n",
  "            if not (is_key_brand(nm) or is_key_brand(r.get('brand_name','') or '')): continue  # _feeds_v2\n"),
 ('"bébé","baby","bb "]',
  '"bébé","baby","bb ","tout-petit","petits enfants","grands enfants","bébés","little kids","big kids","grade school","preschool"]'),
 ("'brand':extract_brand(nm)}\n",
  "'brand':extract_brand(r.get('brand_name') or nm)}\n            if e['brand'] and e['brand'].lower() not in e['name'].lower(): e['name']=e['brand']+' '+e['name']\n"),
 ("            if e['name'] not in seen: seen.add(e['name']); out.append(e)",
  "            k=e.get('img') or e['name']\n            if k not in seen: seen.add(k); out.append(e)"),
 ("    n=re.sub(r'\\s+(Running|Sale)\\s*$','',n)\n",
  "    n=re.sub(r'\\s+Size\\s+[0-9].*$','',n,flags=re.IGNORECASE)\n    n=re.sub(r'\\b(Women|Men|Sneakers?)\\b','',n)\n    n=re.sub(r'\\s+(Running|Sale)\\s*$','',n)\n"),
]
for a, b in R:
    if s.count(a) != 1:
        sys.exit("Ancre introuvable ou multiple — rien modifié : " + a.strip()[:60])
for a, b in R:
    s = s.replace(a, b, 1)
shutil.copy(P, P + ".bak_v2")
open(P, "w", encoding="utf-8").write(s)
print("OK — flux Snipes FR / Solebox EN pris en charge (sauvegarde %s.bak_v2)" % P)
