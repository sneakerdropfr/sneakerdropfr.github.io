"""
migrate_past_releases.py
Cron quotidien (3h UTC) — déplace les releases passées de releases.json vers releases_past.json
Token GitHub lu depuis la variable d'environnement GH_TOKEN
"""
import requests, json, base64, os, re
from datetime import date, datetime, timezone

TOKEN  = os.environ.get("GH_TOKEN", "")
REPO   = "sneakerdropfr/sneakerdropfr.github.io"
BRANCH = "main"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def gh_get(path):
    r = requests.get(f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    content = base64.b64decode(data["content"]).decode()
    return json.loads(content), data["sha"]

def gh_put(path, content_obj, sha, message):
    encoded = base64.b64encode(json.dumps(content_obj, ensure_ascii=False, indent=2).encode()).decode()
    payload = {"message": message, "content": encoded, "sha": sha, "branch": BRANCH}
    r = requests.put(f"https://api.github.com/repos/{REPO}/contents/{path}", headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json()["commit"]["sha"]

def is_past(date_str):
    if not date_str or date_str == "TBD":
        return False
    try:
        return date.fromisoformat(date_str) < date.today()
    except:
        return False

def clean_title(title):
    title = re.sub(r'\s+Releases\s+\w+\s+\d{4}$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+Returns\s+\w+\s+\d{4}$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+Drops\s+\w+\s+\d{4}$', '', title, flags=re.IGNORECASE)
    return title.strip()

def main():
    today = date.today()
    print(f"[{datetime.now(timezone.utc).isoformat()}] Migration releases -> releases_past")

    releases, rel_sha = gh_get("releases.json")
    past, past_sha   = gh_get("releases_past.json")

    print(f"releases.json: {len(releases)} | releases_past.json: {len(past)}")

    to_move = [r for r in releases if is_past(r.get("date", ""))]
    to_keep = [r for r in releases if not is_past(r.get("date", ""))]

    if not to_move:
        print("Aucune paire a migrer.")
        return

    print(f"Paires a migrer: {len(to_move)}")
    for r in to_move:
        print(f"  -> {r.get('date')} | {r.get('title','?')[:60]}")

    existing_ids    = {r.get("id", "") for r in past}
    existing_titles = {r.get("title", "").lower() for r in past}

    added = 0
    for r in to_move:
        r["title"] = clean_title(r.get("title", ""))
        rid    = r.get("id", "")
        rtitle = r.get("title", "").lower()
        if rid not in existing_ids and rtitle not in existing_titles:
            past.append(r)
            existing_ids.add(rid)
            existing_titles.add(rtitle)
            added += 1

    past.sort(key=lambda r: r.get("date","") or "0000-00-00", reverse=True)

    msg = f"auto: migration {len(to_move)} paires passees -> releases_past ({today})"
    sha1 = gh_put("releases.json",      to_keep, rel_sha,  msg)
    sha2 = gh_put("releases_past.json", past,    past_sha, msg)

    print(f"releases.json: {sha1[:8]} ({len(to_keep)} restantes)")
    print(f"releases_past.json: {sha2[:8]} ({len(past)} total, {added} ajoutees)")

if __name__ == "__main__":
    main()
