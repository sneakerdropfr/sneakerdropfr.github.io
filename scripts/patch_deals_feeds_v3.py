#!/usr/bin/env python3
"""deals_affilies.py : modèles enfants entre parenthèses (GS/PS/TD) écartés, coloris ajouté aux noms Snipes, taille retirée des noms Reebok."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "_feeds_v3" in s:
    print("Déjà patché."); sys.exit(0)
if "_feeds_v2" not in s or "def load_reebok(" not in s:
    sys.exit("Les patchs feeds_v2 et Reebok doivent être appliqués avant — rien modifié")
BR = "            if e['brand'] and e['brand'].lower() not in e['name'].lower(): e['name']=e['brand']+' '+e['name']\n"
RBN = "            nm = re.sub(r',\\s*[0-9][0-9.,/ ]*$', '', nm).strip(' ,')\n"
R = [
 ('"grade school","preschool"]', '"grade school","preschool","(gs)","(ps)","(td)","(bg)","(gg)","(inf)"]'),
 (BR, BR + "            col=(r.get('colour') or '').strip()  # _feeds_v3\n"
          "            if m=='Snipes EU' and col and col.lower() not in e['name'].lower(): e['name']=e['name']+' – '+col\n"),
 (RBN, "            nm = re.sub(r',?\\s*Taille\\s*:.*$', '', nm, flags=re.IGNORECASE)\n" + RBN),
]
for a, b in R:
    if s.count(a) != 1:
        sys.exit("Ancre introuvable ou multiple — rien modifié : " + a.strip()[:60])
for a, b in R:
    s = s.replace(a, b, 1)
shutil.copy(P, P + ".bak_v3")
open(P, "w", encoding="utf-8").write(s)
print("OK — enfants (GS/PS/TD), coloris Snipes et tailles Reebok corrigés (sauvegarde %s.bak_v3)" % P)
