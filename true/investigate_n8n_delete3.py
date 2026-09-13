#!/usr/bin/env python3
"""Analyse le contrôleur public API des workflows n8n 2.30.7 :
trouve la route DELETE /workflows/:id, ses guards, et le code qui renvoie
403 Forbidden. Vérifie aussi le schéma workflow_entity (protection)."""
import re
import sqlite3
from pathlib import Path

N8N_DIR = Path("/home/redou/.nvm/versions/node/v22.23.1/lib/node_modules/n8n")
DB = Path.home() / ".n8n" / "database.sqlite"

pub = list(N8N_DIR.glob("dist/public-api/workflows/*.js"))
print("Fichiers public-api/workflows:", [p.name for p in pub])

for p in pub:
    txt = p.read_text(errors="ignore")
    if "delete" not in txt.lower():
        continue
    print(f"\n=== {p.name} ===")
    # trouver les décorateurs @Delete
    for m in re.finditer(r"@Delete\(([^)]*)\)", txt):
        print("  @Delete(", m.group(1), ")")
    # chercher la méthode deleteWorkflow et son code
    for m in re.finditer(r"async delete\w*\([^)]*\)[^{]*\{", txt):
        print("  méthode:", m.group(0)[:200])
    # chercher les messages Forbidden / 403
    for m in re.finditer(r".{80}Forbidden.{80}", txt):
        print("  Forbidden ctx:", m.group(0).replace("\n", " ")[:200])
    # les imports de guards
    for m in re.finditer(r"require\([^)]*globalMiddleware[^)]*\)|globalMiddleware", txt[:3000]):
        print("  guard import:", m.group(0)[:150])

# schéma workflow_entity
con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("PRAGMA table_info(workflow_entity)")
cols = [c[1] for c in cur.fetchall()]
print("\nColonnes workflow_entity:", cols)
# workflows_tags
cur.execute("PRAGMA table_info(workflows_tags)")
print("Colonnes workflows_tags:", [c[1] for c in cur.fetchall()])
con.close()
