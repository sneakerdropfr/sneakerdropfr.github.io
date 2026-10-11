#!/usr/bin/env python3
"""deals_affilies.py : boutons de filtre par modèle dans l'onglet Reebok (Club C, Classic Leather, Nano…)."""
import sys, shutil
P = sys.argv[1] if len(sys.argv) > 1 else "/root/deals_affilies.py"
s = open(P, encoding="utf-8").read()
if "def reebok_family(" in s:
    print("Déjà patché."); sys.exit(0)
if "def load_reebok(" not in s:
    sys.exit("Le patch de l'onglet Reebok doit être appliqué avant — rien modifié")
FUNC = '''REEBOK_FAMILIES = [('club c','Club C'),('classic leather','Classic Leather'),('nano','Nano'),('princess','Princess'),
    ('freestyle','Freestyle'),('floatride','Floatride'),('instapump','Instapump'),('question','Question'),('answer','Answer'),
    ('bb 4000','BB 4000'),('lt court','LT Court'),('workout','Workout'),('ex-o-fit','Ex-O-Fit'),('premier road','Premier Road'),
    ('zig','Zig'),('dmx','DMX'),('energen','Energen'),('world 70','World 70'),('fluxlite','Fluxlite'),('hiit','HIIT'),
    ('court','Court'),('club','Club')]
def reebok_family(nm):
    low = nm.lower()
    for k, v in REEBOK_FAMILIES:
        if k in low: return v
    if 'course' in low or 'running' in low: return 'Running'
    if 'entraînement' in low or 'training' in low: return 'Training'
    if 'basket' in low and 'basketball' in low: return 'Basketball'
    return 'Autres'
def top_cats(items, n=12):
    from collections import Counter
    return [c for c, _ in Counter(i.get('cat', '') for i in items if i.get('cat') and i.get('cat') != 'Autres').most_common(n)]
'''
R = [
 ("def load_reebok():", FUNC + "def load_reebok():"),
 ("'brand': 'Reebok'})", "'brand': 'Reebok', 'cat': reebok_family(nm)})"),
 ('<div class="cnt" id="n-reebok"></div>',
  '''<div class="brands" id="br-reebok">{bb_html(top_cats(rb),'reebok')}</div>\n  <div class="cnt" id="n-reebok"></div>'''),
 ("    if(br&&i.brand!==br)return false;", "    if(br&&i.brand!==br&&i.cat!==br)return false;"),
]
for a, b in R:
    if s.count(a) != 1:
        sys.exit("Ancre introuvable ou multiple — rien modifié : " + a.strip()[:60])
for a, b in R:
    s = s.replace(a, b, 1)
shutil.copy(P, P + ".bak_rbf")
open(P, "w", encoding="utf-8").write(s)
print("OK — filtres par modèle ajoutés à l'onglet Reebok (sauvegarde %s.bak_rbf)" % P)
