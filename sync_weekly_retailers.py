#!/usr/bin/env python3
import json, os, subprocess
from datetime import datetime

REPO_DIR = "/root/sneakerdropfr.github.io"
WEEKLY_FILE = "/opt/sneaker-restock-bot/weekly_data.json"
RELEASES_FILE = os.path.join(REPO_DIR, "releases.json")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

def log(msg):
    print(f"[sync_retailers] {datetime.now().strftime('%H:%M:%S')} {msg}", flush=True)

with open(RELEASES_FILE, encoding="utf-8") as f:
    releases = json.load(f)

rel_by_title = {r.get("title","").strip().lower(): r for r in releases}
rel_by_id = {r.get("id",""): r for r in releases}

with open(WEEKLY_FILE, encoding="utf-8") as f:
    wd = json.load(f)

updated = 0
for item in wd.get("releases", []):
    name = (item.get("name") or item.get("title","")).strip()
    rid = item.get("id","")
    match = rel_by_id.get(rid) or rel_by_title.get(name.lower())
    if match and match.get("retailers"):
        item["retailers"] = match["retailers"]
        if not rid and match.get("id"):
            item["id"] = match["id"]
        updated += 1

log(f"{updated} releases enrichies avec retailers")

with open(WEEKLY_FILE, "w", encoding="utf-8") as f:
    json.dump(wd, f, ensure_ascii=False, indent=2)

subprocess.run(["cp", WEEKLY_FILE, REPO_DIR], check=True)
subprocess.run(["git", "-C", REPO_DIR, "pull", "origin", "main", "--quiet"], check=True)
subprocess.run(["git", "-C", REPO_DIR, "add", "weekly_data.json"], check=True)

result = subprocess.run(["git", "-C", REPO_DIR, "diff", "--cached", "--quiet"])
if result.returncode != 0:
    subprocess.run(["git", "-C", REPO_DIR, "commit", "-m", "auto: sync weekly retailers"], check=True)
    if TOKEN:
        subprocess.run([
            "git", "-C", REPO_DIR, "push",
            f"https://{TOKEN}@github.com/sneakerdropfr/sneakerdropfr.github.io.git",
            "main"
        ], check=True)
        log("Pousse sur GitHub")
    else:
        log("GITHUB_TOKEN manquant")
else:
    log("Aucun changement a pousser")
