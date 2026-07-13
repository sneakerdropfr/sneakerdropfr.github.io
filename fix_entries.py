#!/usr/bin/env python3
import json
import subprocess
import sys

path = "releases.json"
data = json.load(open(path))

fixes = {
    "KH8048": "https://justfreshkicks.com/wp-content/uploads/2026/07/Screenshot-2026-07-10-at-2.44.21-PM.jpg",
    "LC1125": "https://justfreshkicks.com/wp-content/uploads/2026/07/naked-adidas-evo-sl-zip-lc1125-1.webp",
    "IU1869-600": "https://www.theillest.pl/wp-content/uploads/2026/07/Nike-Zoom-Skylon-11-University-Red-IU1869-600.jpeg",
}

print("=== Vérification HTTP des nouvelles URLs ===")
all_ok = True
for sku, url in fixes.items():
    code = subprocess.run(
        ["curl", "-sL", "-o", "/dev/null", "-w", "%{http_code}", url],
        capture_output=True, text=True, timeout=15
    ).stdout.strip()
    status = "OK" if code == "200" else "PROBLEME"
    print(f"  {code} [{status}] {sku} — {url}")
    if code != "200":
        all_ok = False

if not all_ok:
    print("\n⚠️  Au moins une image ne répond pas en 200. Rien n'a été écrit.")
    if "--force" not in sys.argv:
        sys.exit(1)

changed = 0
for r in data:
    sku = r.get("sku", "")
    if sku in fixes:
        old = r.get("image_url", "(vide)")
        r["image_url"] = fixes[sku]
        changed += 1
        print(f"Corrigé {sku}: {old} -> {fixes[sku]}")

json.dump(data, open(path, "w"), ensure_ascii=False, indent=2)
print(f"\n{changed} entrées corrigées. Total: {len(data)} entrées.")
