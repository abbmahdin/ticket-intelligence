#!/usr/bin/env python3
"""Trouve où la route DELETE /workflows/:id est définie dans n8n 2.30.7
et vérifie la colonne audience de la clé API (restriction possible)."""
import re
import sqlite3
from pathlib import Path

N8N_DIR = Path("/home/redou/.nvm/versions/node/v22.23.1/lib/node_modules/n8n")
DB = Path.home() / ".n8n" / "database.sqlite"

# 1) audience de la clé
con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("SELECT id, label, scopes, audience FROM user_api_keys WHERE label='quantlive'")
for r in cur.fetchall():
    print("Clé quantlive:", r)
con.close()

# 2) chercher les routes @Delete dans tout dist
print("\n=== Routes @Delete avec 'workflow' dans dist ===")
hits = []
for p in list(N8N_DIR.glob("dist/**/*.js")):
    try:
        txt = p.read_text(errors="ignore")
    except Exception:
        continue
    if "@Delete" not in txt:
        continue
    for m in re.finditer(r"@Delete\(\s*['\"]([^'\"]*)['\"]", txt):
        route = m.group(1)
        if "workflow" in route.lower() or route == "/:id" or "delete" in route.lower():
            hits.append((str(p.relative_to(N8N_DIR)), route, m.start()))
for h in hits[:20]:
    print(" ", h[0], "|", h[1])

# 3) chercher le controller public-api workflows
print("\n=== Controllers public-api ===")
for p in list(N8N_DIR.glob("dist/public-api/**/*workflow*.js")):
    print(" ", p.relative_to(N8N_DIR))
for p in list(N8N_DIR.glob("dist/public-api/**/*.js")):
    name = p.name
    if "workflow" in name.lower():
        print(" ", p.relative_to(N8N_DIR))

# 4) message Forbidden dans les controllers
print("\n=== Contextes 'Forbidden' (échantillon) ===")
cnt = 0
for p in list(N8N_DIR.glob("dist/public-api/**/*.js")):
    try:
        txt = p.read_text(errors="ignore")
    except Exception:
        continue
    for m in re.finditer(r".{60}Forbidden.{60}", txt):
        print(" ", p.name, ":", m.group(0).replace("\n", " ")[:180])
        cnt += 1
        if cnt > 12:
            break
    if cnt > 12:
        break
