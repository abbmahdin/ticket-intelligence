#!/usr/bin/env python3
"""Supprime le workflow n8n dupliqué inactif « QuantLive - Economic Calendar
(ForexFactory) » (id=quantlivecal01, du 20/07) et vérifie que l'actif
(id=1, du 17/07) reste en place.
"""
import json
import os
import sys
import urllib.request

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
BASE = "http://localhost:5678/api/v1"
TARGET = "quantlivecal01"  # doublon inactif (mis à jour le 20/07)
KEEP = "1"                 # actif (créé le 17/07)


def api(method, path, body=None, timeout=25):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={
        "X-N8N-API-KEY": KEY, "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode()[:300]}


def main():
    # 1) Garde-fou : le workflow cible doit être inactif avant suppression
    w = api("GET", f"/workflows/{TARGET}")
    if "__error__" in w:
        print(f"ECHEC GET cible: {w}")
        return 1
    if w.get("active"):
        print("REFUS: le workflow cible est ACTIF — annulation (garde-fou)")
        return 1
    print(f"Cible confirmee: {w.get('name')} | active={w.get('active')} | updatedAt={w.get('updatedAt')}")

    # 2) Suppression
    r = api("DELETE", f"/workflows/{TARGET}")
    if "__error__" in r:
        print(f"ECHEC DELETE: {r}")
        return 1
    print("DELETE OK")

    # 3) Verification finale
    wfs = api("GET", "/workflows?limit=100").get("data", [])
    remaining = [w for w in wfs if "Economic Calendar" in w.get("name", "")]
    print(f"Workflows Economic Calendar restants : {len(remaining)}")
    for w in remaining:
        print(f"  id={w['id']} | active={w.get('active')} | createdAt={w.get('createdAt')}")

    kept = [w for w in remaining if w["id"] == KEEP and w.get("active")]
    if len(remaining) == 1 and kept:
        print("OK: doublon supprime, actif conserve")
        return 0
    print("ATTENTION: etat inattendu — verifier manuellement")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
