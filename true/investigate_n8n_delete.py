#!/usr/bin/env python3
"""Investigue pourquoi DELETE /workflows/quantlivecal01 renvoie 403 :
- version n8n (via /healthz ou settings)
- scopes de la clé API (table n8n_api_keys de la DB SQLite)
- propriétaire du workflow cible
"""
import json
import os
import sqlite3
import urllib.request
from pathlib import Path

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
    # 1) Version n8n
    try:
        r = urllib.request.urlopen("http://localhost:5678/healthz", timeout=5)
        print("healthz:", r.status, r.read().decode()[:100])
    except Exception as e:
        print("healthz erreur:", e)

    # 2) Clé API actuelle : hash partiel pour retrouver la ligne en DB
    print("\nClé utilisée (derniers 8):", KEY[-8:])

    # 3) DB n8n — chercher la table des clés API
    db_candidates = [
        Path.home() / ".n8n" / "database.sqlite",
        Path.home() / ".n8n" / "quantlive.sqlite",
    ]
    for db in db_candidates:
        if not db.exists():
            continue
        print(f"\nDB trouvée: {db} ({db.stat().st_size} octets)")
        try:
            con = sqlite3.connect(db)
            cur = con.cursor()
            # tables
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [r[0] for r in cur.fetchall()]
            print("Tables (échantillon):", [t for t in tables if "api" in t.lower() or "workflow" in t.lower() or "user" in t.lower() or "shared" in t.lower()][:20])
            # clés API
            if "n8n_api_keys" in tables:
                cur.execute("PRAGMA table_info(n8n_api_keys)")
                print("Colonnes n8n_api_keys:", [c[1] for c in cur.fetchall()])
                cur.execute("SELECT id, label, userId, scopes, createdAt FROM n8n_api_keys")
                for row in cur.fetchall():
                    print("  api_key row:", row)
            # workflow cible
            if "workflow_entity" in tables:
                cur.execute("SELECT id, name, active, createdAt, updatedAt FROM workflow_entity WHERE id IN ('1','quantlivecal01')")
                for row in cur.fetchall():
                    print("  workflow:", row)
            # partage / propriétaire
            for t in tables:
                if "shared" in t.lower() and "workflow" in t.lower():
                    cur.execute(f"PRAGMA table_info({t})")
                    cols = [c[1] for c in cur.fetchall()]
                    print(f"  table {t} colonnes: {cols}")
                    try:
                        cur.execute(f"SELECT * FROM {t} WHERE workflowId='quantlivecal01' OR workflowId='1'")
                        for row in cur.fetchall():
                            print(f"  {t} row:", row)
                    except Exception as e:
                        print(f"  {t} query err:", e)
            con.close()
        except Exception as e:
            print(f"  DB err: {e}")

    # 4) Tester un DELETE sur le workflow cible via l'API (reproduire)
    print("\nTest DELETE (repro):")
    r = api("DELETE", "/workflows/quantlivecal01")
    print("  DELETE quantlivecal01:", r)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
