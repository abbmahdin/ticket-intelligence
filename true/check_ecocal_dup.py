#!/usr/bin/env python3
"""Vérifie les 2 workflows « QuantLive - Economic Calendar (ForexFactory) »
avant suppression du doublon inactif (id=quantlivecal01, du 20/07) :
affiche id, active, createdAt, updatedAt et le trigger de chacun.
"""
import json
import os
import urllib.request

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
BASE = "http://localhost:5678/api/v1"


def api(method, path, body=None, timeout=25):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={
        "X-N8N-API-KEY": KEY, "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode()[:300]}


def main():
    wfs = api("GET", "/workflows?limit=100").get("data", [])
    targets = [w for w in wfs if "Economic Calendar" in w.get("name", "")]
    print(f"Workflows Economic Calendar trouvés : {len(targets)}\n")
    for w in targets:
        full = api("GET", f"/workflows/{w['id']}")
        trigs = []
        for n in full.get("nodes", []):
            t = n.get("type", "")
            if "trigger" in t or "webhook" in t:
                trigs.append(f"{n.get('name')} ({t})")
        print(f"  id={w['id']} | active={w.get('active')} | createdAt={w.get('createdAt')} | updatedAt={w.get('updatedAt')}")
        print(f"    triggers: {trigs if trigs else 'aucun'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
