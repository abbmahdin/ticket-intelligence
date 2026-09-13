#!/usr/bin/env python3
"""Vérifie les scopes de la clé API n8n (table user_api_keys) et les
commandes CLI n8n disponibles pour la gestion des clés / suppression."""
import hashlib
import hmac
import json
import os
import sqlite3
import subprocess
from pathlib import Path

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
DB = Path.home() / ".n8n" / "database.sqlite"


def main():
    print("=== Scopes de la clé API ===")
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("PRAGMA table_info(user_api_keys)")
    cols = [c[1] for c in cur.fetchall()]
    print("Colonnes user_api_keys:", cols)
    cur.execute("SELECT * FROM user_api_keys")
    rows = cur.fetchall()
    for row in rows:
        d = dict(zip(cols, row))
        label = d.get("label", "?")
        scopes = d.get("scopes")
        api_key_hash = d.get("apiKey", "")
        print(f"  label={label} | scopes={scopes} | createdAt={d.get('createdAt')} | id={d.get('id')}")
        # La clé est stockée hashée (HMAC) — impossible de matcher directement,
        # mais on affiche les infos utiles pour identifier la clé courante.
    con.close()

    print("\n=== Version n8n ===")
    try:
        r = subprocess.run(
            ["node", "/home/redou/.nvm/versions/node/v22.23.1/lib/node_modules/n8n/bin/n8n", "--version"],
            capture_output=True, text=True, timeout=15,
        )
        print("n8n --version:", r.stdout.strip() or r.stderr.strip())
    except Exception as e:
        print("version err:", e)

    print("\n=== CLI n8n : commandes user-management ===")
    try:
        r = subprocess.run(
            ["node", "/home/redou/.nvm/versions/node/v22.23.1/lib/node_modules/n8n/bin/n8n", "user-management:help"],
            capture_output=True, text=True, timeout=15,
        )
        print(r.stdout[:1500] or r.stderr[:500])
    except Exception as e:
        print("cli help err:", e)

    print("\n=== CLI n8n : workflow delete ? ===")
    try:
        r = subprocess.run(
            ["node", "/home/redou/.nvm/versions/node/v22.23.1/lib/node_modules/n8n/bin/n8n", "workflow:delete", "--help"],
            capture_output=True, text=True, timeout=15,
        )
        print((r.stdout or r.stderr)[:1200])
    except Exception as e:
        print("workflow delete err:", e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
