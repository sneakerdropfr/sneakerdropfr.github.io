#!/usr/bin/env python3
"""
À exécuter sur la VPS depuis /root/sneakerdropfr.github.io
Ajoute KH8048, LC1125, IU1869-700, IU1869-600
Vérifie les URLs d'images en HTTP avant d'écrire dans releases.json
"""
import json
import subprocess
import sys

path = "releases.json"
data = json.load(open(path))
existing_skus = {r.get("sku") for r in data}

new_entries = [
    {
        "id": "adidas-terra-mono-lightstrike-white-black-kh8048",
        "title": "Adidas Terra Mono Lightstrike \"White Black\"",
        "brand": "Adidas",
        "sku": "KH8048",
        "colorway": "Core White/Off White/Core Black",
        "date": "2026-07-15",
        "price": 180,
        "year": 2026,
        "image_url": "https://justfreshkicks.com/wp-content/uploads/2026/07/Screenshot-2026-07-10-at-2.44.21-PM.jpg",
        "featured": False,
        "retailers": [{"name": "BSTN", "url": "https://www.awin1.com/cread.php?awinmid=104979&awinaffid=2855487&p=https%3A%2F%2Fwww.bstn.com%2Fus_en%2Fp%2Fadidas-terra-mono-lightstrike-kh8048-0355238", "price": "180$", "resell": False, "raffle": False}],
        "source": "JustFreshKicks",
    },
    {
        "id": "naked-copenhagen-adidas-adizero-evo-sl-zip-pink-silver-lc1125",
        "title": "Naked Copenhagen x Adidas Adizero Evo SL Zip \"Pink Silver\"",
        "brand": "Adidas",
        "sku": "LC1125",
        "colorway": "Pink/Metallic Silver",
        "date": "2026-07-15",
        "price": 180,
        "year": 2026,
        "image_url": "https://justfreshkicks.com/wp-content/uploads/2026/07/naked-adidas-evo-sl-zip-lc1125-1.webp",
        "featured": False,
        "retailers": [],
        "source": "JustFreshKicks",
    },
    {
        "id": "nike-zoom-skylon-11-volt-iu1869-700",
        "title": "Nike Zoom Skylon 11 \"Volt\"",
        "brand": "Nike",
        "sku": "IU1869-700",
        "colorway": "Volt",
        "date": "2026-07-14",
        "price": 130,
        "year": 2026,
        "image_url": "",
        "featured": False,
        "retailers": [],
        "source": "WhenToCop",
    },
    {
        "id": "nike-zoom-skylon-11-university-red-iu1869-600",
        "title": "Nike Zoom Skylon 11 \"University Red\"",
        "brand": "Nike",
        "sku": "IU1869-600",
        "colorway": "University Red",
        "date": "2026-07-14",
        "price": 130,
        "year": 2026,
        "image_url": "",
        "featured": False,
        "retailers": [],
        "source": "WhenToCop",
    },
]

print("=== Vérification des images ===")
all_ok = True
for e in new_entries:
    url = e.get("image_url", "")
    if not url:
        print(f"  SKIP (pas d'image encore) : {e['sku']}")
        continue
    try:
        code = subprocess.run(
            ["curl", "-sL", "-o", "/dev/null", "-w", "%{http_code}", url],
            capture_output=True, text=True, timeout=15
        ).stdout.strip()
    except Exception as ex:
        code = f"ERREUR ({ex})"
    status = "OK" if code == "200" else "PROBLEME"
    print(f"  {code} [{status}] {e['sku']} — {url}")
    if code != "200":
        all_ok = False

if not all_ok:
    print("\n⚠️  Au moins une image ne répond pas en 200. Corrige avant de continuer, ou lance avec --force.")
    if "--force" not in sys.argv:
        sys.exit(1)

added = 0
for e in new_entries:
    if e["sku"] not in existing_skus:
        data.append(e)
        added += 1
        print(f"Ajouté: {e['title']}")
    else:
        print(f"Déjà présent: {e['title']}")

json.dump(data, open(path, "w"), ensure_ascii=False, indent=2)
print(f"\nTotal: {len(data)} entrées ({added} ajoutées)")
