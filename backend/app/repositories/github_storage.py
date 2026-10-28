"""GitHub-backed file storage for the free-tier deploy (no persistent disk).

A private repo acts as the memory store, which also gives free version
history. Requires:
  GH_REPO   e.g. "yourname/agent-memory"
  GH_TOKEN  fine-grained PAT with Contents: read+write on that repo
"""
import base64
import os

import requests

REPO = os.environ.get("GH_REPO", "")
TOKEN = os.environ.get("GH_TOKEN", "")
API = f"https://api.github.com/repos/{REPO}/contents"
H = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}

_sha: dict[str, str] = {}


def read(path: str) -> str:
    r = requests.get(f"{API}/{path}", headers=H, timeout=15)
    if r.status_code == 404:
        return ""
    r.raise_for_status()
    j = r.json()
    _sha[path] = j["sha"]
    return base64.b64decode(j["content"]).decode()


def write(path: str, text: str, message: str = "update memory") -> None:
    body = {
        "message": message,
        "content": base64.b64encode(text.encode()).decode(),
    }
    if path not in _sha:
        # May exist without having been read yet (fresh process) — fetch sha.
        r = requests.get(f"{API}/{path}", headers=H, timeout=15)
        if r.status_code == 200:
            _sha[path] = r.json()["sha"]
    if path in _sha:
        body["sha"] = _sha[path]
    r = requests.put(f"{API}/{path}", headers=H, json=body, timeout=15)
    r.raise_for_status()
    _sha[path] = r.json()["content"]["sha"]

