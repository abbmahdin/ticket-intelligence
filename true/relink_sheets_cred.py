#!/usr/bin/env python3
"""Relie les workflows bloqués (Equity Alert + Gestion Bankroll) à la
credential Google Sheets réelle (id=kEHmuVU7La1JvIP6) puis les active.

Idempotent : ne modifie que les nodes googleSheets dont la credential
pointe encore sur le placeholder "REPLACE".
"""
import json
import os
import sys
import urllib.request

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
SHEETS_CRED_ID = "kEHmuVU7La1JvIP6"
SHEETS_CRED_NAME = "Google Sheets account"
BASE = "http://localhost:5678/api/v1"
H = {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"}

TARGETS = ["Equity Alert Bot", "Bankroll & Stakes"]


def api(method, path, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode()[:300]}


def main():
    wfs = api("GET", "/workflows?limit=100").get("data", [])
    done = 0
    for w in wfs:
        name = w.get("name", "")
        if not any(t in name for t in TARGETS):
            continue
        wid = w["id"]
        full = api("GET", f"/workflows/{wid}")
        if "__error__" in full:
            print(f"[SKIP] {name}: GET error {full['__error__']} {full.get('__body__')}")
            continue

        changed = False
        for n in full.get("nodes", []):
            t = n.get("type", "")
            if "googleSheets" not in t:
                continue
            n.setdefault("credentials", {})
            gs = n["credentials"].get("googleSheetsOAuth2Api") or {}
            if gs.get("id") in (None, "REPLACE"):
                n["credentials"]["googleSheetsOAuth2Api"] = {
                    "id": SHEETS_CRED_ID,
                    "name": SHEETS_CRED_NAME,
                }
                changed = True
                print(f"  [{name}] node '{n.get('name')}': REPLACE -> {SHEETS_CRED_ID}")

        if not changed:
            print(f"[OK] {name}: déjà relié (active={full.get('active')})")
            done += 1
            continue

        # NB: le body PUT ne doit PAS contenir 'active' (read-only en API)
        payload = {
            "name": full["name"],
            "nodes": full["nodes"],
            "connections": full["connections"],
            "settings": full.get("settings", {}),
        }
        r = api("PUT", f"/workflows/{wid}", payload)
        if "__error__" in r:
            print(f"[FAIL] {name}: PUT error {r['__error__']} {r.get('__body__')}")
            continue
        # Activation explicite
        r2 = api("POST", f"/workflows/{wid}/activate")
        if "__error__" in r2:
            print(f"[WARN] {name}: activate error {r2['__error__']} {r2.get('__body__')}")
        done += 1
        print(f"[ACTIVE] {name} -> relié + activé")

    # Vérification finale (fait échouer le script si un workflow n'est pas réellement actif)
    print("\n=== Vérification finale ===")
    wfs = api("GET", "/workflows?limit=100").get("data", [])
    bad = []
    for w in wfs:
        if any(t in w.get("name", "") for t in TARGETS):
            full = api("GET", f"/workflows/{w['id']}")
            ok = all(
                (n.get("credentials") or {})
                .get("googleSheetsOAuth2Api", {})
                .get("id")
                == SHEETS_CRED_ID
                for n in full.get("nodes", [])
                if "googleSheets" in n.get("type", "")
            )
            print(f"  {w['name']}: active={w.get('active')} sheets_relié={ok}")
            if not (w.get("active") and ok):
                bad.append(w["name"])
    print(f"\nWorkflows traités: {done}/2")
    if done != 2 or bad:
        print(f"ECHEC: workflows non conformes: {bad}")
        sys.exit(1)


if __name__ == "__main__":
    main()
