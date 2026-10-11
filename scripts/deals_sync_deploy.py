#!/usr/bin/env python3
"""Après run_deals.sh : copie deals.html de main vers perplexity, puis lance le déploiement GitHub Pages."""
import os, re, json, base64, subprocess, sys, urllib.request, urllib.error
REPO = "sneakerdropfr/sneakerdropfr.github.io"
CLONE = "/root/sneakerdropfr.github.io"
API = "https://api.github.com/repos/" + REPO

def token():
    t = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if t: return t
    try:
        url = subprocess.run(["git", "-C", CLONE, "remote", "get-url", "origin"], capture_output=True, text=True).stdout
        m = re.search(r"https://(?:[^:@/]+:)?([^@/]+)@github\.com", url)
        if m: return m.group(1)
    except Exception: pass
    sys.exit("[deals_sync] Aucun token trouvé (GITHUB_TOKEN, GH_TOKEN ou URL du remote) — rien fait")

T = token()
def call(method, path, data=None):
    req = urllib.request.Request(API + path, method=method,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Authorization": "token " + T, "Accept": "application/vnd.github+json", "User-Agent": "deals-sync"})
    with urllib.request.urlopen(req, timeout=30) as r:
        b = r.read(); return json.loads(b) if b else {}

def get(branch):
    j = call("GET", "/contents/deals.html?ref=" + branch)
    if j.get("content"): return base64.b64decode(j["content"]), j["sha"]
    blob = call("GET", "/git/blobs/" + j["sha"])
    return base64.b64decode(blob["content"]), j["sha"]

try:
    main_c, _ = get("main")
    perp_c, perp_sha = get("perplexity")
    if main_c == perp_c:
        print("[deals_sync] perplexity déjà identique à main")
    else:
        call("PUT", "/contents/deals.html", {"message": "[skip ci] sync: deals.html perplexity ← main",
             "content": base64.b64encode(main_c).decode(), "sha": perp_sha, "branch": "perplexity"})
        print("[deals_sync] deals.html copié sur perplexity")
    call("POST", "/actions/workflows/pages.yml/dispatches", {"ref": "main"})
    print("[deals_sync] déploiement GitHub Pages lancé")
except urllib.error.HTTPError as e:
    sys.exit("[deals_sync] Erreur GitHub %s : %s" % (e.code, e.read()[:200].decode(errors="ignore")))
