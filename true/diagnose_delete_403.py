#!/usr/bin/env python3
"""Diagnostic du 403 DELETE :
1) Tester DELETE sur un AUTRE workflow inactif (si 403 aussi -> problème général
   d'API/clé ; si OK -> problème spécifique au workflow cible).
2) Vérifier workflow_dependency, isArchived, versionId pour quantlivecal01.
3) Lire le middleware global.middleware.js (publicApiScope + projectScope).
"""
import json
import os
import re
import sqlite3
import urllib.request
from pathlib import Path

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
BASE = "http://localhost:5678/api/v1"
DB = Path.home() / ".n8n" / "database.sqlite"
N8N_DIR = Path("/home/redou/.nvm/versions/node/v22.23.1/lib/node_modules/n8n")


def api(method, path, body=None, timeout=25):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={
        "X-N8N-API-KEY": KEY, "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode()[:200]}


def main():
    # 1) Tester DELETE sur un autre workflow inactif (Concordia - Test Node)
    test_wf = None
    wfs = api("GET", "/workflows?limit=100").get("data", [])
    for w in wfs:
        if "Concordia - Test Node" in w.get("name", ""):
            test_wf = w["id"]
            break
    if test_wf:
        print(f"Test DELETE sur workflow inactif: {test_wf}")
        r = api("DELETE", f"/workflows/{test_wf}")
        if "__error__" in r:
            print(f"  -> {r['__error__']} : {r.get('__body__')}  (GENERAL: le DELETE API est restreint)")
        else:
            print("  -> SUCCES ! Le 403 est SPECIFIQUE a quantlivecal01")
    else:
        print("Workflow de test introuvable")

    # 2) Vérifications DB pour quantlivecal01
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT id, name, active, isArchived, versionId, activeVersionId, sourceWorkflowId, meta FROM workflow_entity WHERE id='quantlivecal01'")
    for r in cur.fetchall():
        print("\nquantlivecal01:", r)
    # dépendances
    cur.execute("SELECT * FROM workflow_dependency WHERE workflowId='quantlivecal01'")
    deps = cur.fetchall()
    print(f"\nworkflow_dependency pour quantlivecal01: {len(deps)} ligne(s)")
    for r in deps:
        print("  ", r)
    # est-ce que d'autres workflows dépendent de quantlivecal01 ?
    cur.execute("SELECT id, workflowId, dependencyKey, dependencyInfo FROM workflow_dependency WHERE dependencyKey LIKE '%quantlivecal01%' OR dependencyInfo LIKE '%quantlivecal01%'")
    for r in cur.fetchall():
        print("  dependant externe:", r)
    # workflow_history
    cur.execute("SELECT COUNT(*) FROM workflow_history WHERE workflowId='quantlivecal01'")
    print("workflow_history rows:", cur.fetchone()[0])
    # workflow_statistics
    cur.execute("SELECT COUNT(*) FROM workflow_statistics WHERE workflowId='quantlivecal01'")
    print("workflow_statistics rows:", cur.fetchone()[0])
    # workflows_tags
    cur.execute("SELECT COUNT(*) FROM workflows_tags WHERE workflowId='quantlivecal01'")
    print("workflows_tags rows:", cur.fetchone()[0])
    # shared_workflow
    cur.execute("SELECT * FROM shared_workflow WHERE workflowId='quantlivecal01'")
    for r in cur.fetchall():
        print("shared_workflow:", r)
    con.close()

    # 3) Middleware
    mid = N8N_DIR / "dist/public-api/v1/shared/middlewares/global.middleware.js"
    if mid.exists():
        txt = mid.read_text(errors="ignore")
        m = re.search(r"publicApiScope[^}]{0,600}", txt)
        if m:
            print("\npublicApiScope (extrait):", m.group(0)[:600])
        m = re.search(r"projectScope[^}]{0,800}", txt)
        if m:
            print("\nprojectScope (extrait):", m.group(0)[:800])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
