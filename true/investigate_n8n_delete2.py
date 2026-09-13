#!/usr/bin/env python3
"""Investigation approfondie du 403 DELETE n8n 2.30.7 :
- utilisateur associé à la clé API quantlive + rôles projets
- dépendances du workflow cible (workflow_dependency)
- routes DELETE dans le code du package n8n (public-api)
"""
import json
import os
import re
import sqlite3
import subprocess
from pathlib import Path

DB = Path.home() / ".n8n" / "database.sqlite"
N8N_DIR = Path("/home/redou/.nvm/versions/node/v22.23.1/lib/node_modules/n8n")


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    print("=== Utilisateur de la clé API quantlive ===")
    cur.execute("SELECT id, userId, label, scopes FROM user_api_keys WHERE label='quantlive'")
    rows = cur.fetchall()
    for row in rows:
        print("  api_key:", row)
        uid = row[1]
        # user (introspection dynamique)
        cur.execute("PRAGMA table_info(user)")
        ucols = [c[1] for c in cur.fetchall()]
        cur.execute(f"SELECT {', '.join(ucols)} FROM user WHERE id=?", (uid,))
        for u in cur.fetchall():
            print("  user:", dict(zip(ucols, u)))
        # projet par défaut de l'utilisateur
        for t in ("project", "project_relation", "project_relation_personal"):
            try:
                cur.execute(f"PRAGMA table_info({t})")
                cols = [c[1] for c in cur.fetchall()]
                print(f"  table {t} colonnes: {cols}")
                cur.execute(f"SELECT * FROM {t} LIMIT 8")
                for r in cur.fetchall():
                    print(f"    {t}:", r)
            except Exception as e:
                print(f"  {t} err: {e}")

    print("\n=== Dépendances du workflow cible ===")
    try:
        cur.execute("PRAGMA table_info(workflow_dependency)")
        cols = [c[1] for c in cur.fetchall()]
        print("  colonnes:", cols)
        cur.execute("SELECT * FROM workflow_dependency WHERE workflowId='quantlivecal01' OR dependentOnWorkflowId='quantlivecal01'")
        for r in cur.fetchall():
            print("  dep row:", r)
    except Exception as e:
        print("  workflow_dependency err:", e)

    print("\n=== Routes DELETE dans le code n8n (public-api) ===")
    routes = []
    for p in N8N_DIR.glob("dist/public-api/**/*.js"):
        try:
            txt = p.read_text(errors="ignore")
        except Exception:
            continue
        if "delete" in txt.lower() and ("workflow" in txt.lower()):
            for m in re.finditer(r"(@(?:Delete|delete)\([^)]*\)|delete\s*[:=]\s*\[[^\]]*\]|workflows/:workflowId|workflowId)", txt):
                routes.append((p.name, m.group(0)))
    # plus simple : chercher le controller workflows public
    for name in ("workflows.controller.js", "workflows.controller.ts", "public-api.workflows"):
        for p in N8N_DIR.rglob(f"*{name}*"):
            print(f"  fichier trouvé: {p}")
            txt = p.read_text(errors="ignore")
            for m in re.finditer(r"@Delete\([^)]*\)[^@]{0,400}", txt):
                print("    route:", m.group(0)[:300].replace("\n", " "))
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
