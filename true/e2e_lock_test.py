#!/usr/bin/env python3
"""Test E2E : écritures concurrentes main+worker sans verrou (n8n queue + PG).

1. Crée un workflow webhook -> Code minimal (effet de bord nul).
2. L'active (enregistre le webhook en production).
3. Lit le webhookPath réel depuis webhook_entity.
4. Déclenche N requêtes webhook CONCURRENTES (main = INSERT execution,
   worker = UPDATE execution + execution_data).
5. Attend, puis compte les statuts d'exécution.
6. Sonde les logs n8n (main+worker) et pg_stat_activity pour détecter tout
   deadlock / lock-timeout / SQLITE_BUSY.
7. Nettoie (désactive + supprime le workflow et ses exécutions).
"""
from __future__ import annotations

import concurrent.futures
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid

KEY = open("/home/redou/.n8n_migration_api_key").read().strip()
BASE = "http://localhost:5678"
API = f"{BASE}/api/v1/workflows"
N = 20


def api(method: str, path: str, body=None) -> dict:
    req = urllib.request.Request(
        API + path,
        method=method,
        headers={"X-N8N-API-KEY": KEY, "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return {"__http_error__": e.code, "body": e.read().decode()}


def psql(sql: str) -> str:
    return subprocess.run(
        ["docker", "exec", "quantlive-pg18", "psql", "-U", "quantlive", "-d", "n8n", "-tAc", sql],
        capture_output=True, text=True,
    ).stdout.strip()


def sh(cmd: str) -> str:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout or "") + (r.stderr or "")


def main() -> int:
    ts = int(time.time())
    hook_path = f"e2e-lock-test-{ts}"
    name = "E2E Lock Test (auto-cleanup)"

    # 1. create
    webhook_node = {
        "id": str(uuid.uuid4()),
        "parameters": {"httpMethod": "POST", "path": hook_path,
                       "responseMode": "onReceived", "options": {}},
        "name": "Webhook e2e", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
        "position": [0, 0], "webhookId": str(uuid.uuid4()),
    }
    code_node = {
        "id": str(uuid.uuid4()),
        "parameters": {"jsCode": "return [{ json: { ok: true, ts: new Date().toISOString() } }];"},
        "name": "Code ok", "type": "n8n-nodes-base.code", "typeVersion": 2,
        "position": [220, 0],
    }
    wf = {
        "name": name,
        "nodes": [webhook_node, code_node],
        "connections": {
            webhook_node["name"]: {"main": [[{"node": code_node["name"], "type": "main", "index": 0}]]},
        },
        "settings": {},
    }
    res = api("POST", "", wf)
    if "__http_error__" in res:
        print("CREATE FAILED:", res)
        return 1
    wid = res["id"]
    print(f"created workflow id={wid}")

    # 2. activate
    res = api("POST", f"/{wid}/activate", {})
    print("activate:", res.get("__http_error__", res.get("name", "ok")))
    time.sleep(3)

    # 3. read real webhook path
    hook = psql(f'SELECT "webhookPath" FROM webhook_entity WHERE "workflowId"=\'{wid}\';')
    print("webhookPath:", hook)
    if not hook:
        print("FAIL: no webhook registered")
        return 1
    url = f"{BASE}/webhook/{hook}"

    # 4. fire N concurrent webhook POSTs
    def fire(i: int):
        req = urllib.request.Request(
            url, method="POST",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"i": i}).encode(),
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception as e:  # noqa: BLE001
            return f"ERR:{e}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=N) as ex:
        statuses = list(ex.map(fire, range(N)))
    print(f"webhook HTTP statuses ({N} concurrents):", statuses)

    # 5. wait for executions
    time.sleep(15)
    print("execution statuses:")
    print(psql(
        f'SELECT status, count(*) FROM execution_entity WHERE "workflowId"=\'{wid}\' GROUP BY status ORDER BY status;'
    ).replace("\n", " | ") or "(aucune)")

    # 6. lock probes
    print("\n--- verrouils / erreurs dans les logs n8n (2 derniers min) ---")
    print(sh("journalctl --user -u n8n --no-pager --since '-3 min' 2>&1 | "
             "grep -iE 'deadlock|lock timeout|could not obtain|database is locked|SQLITE_BUSY|40P01|55P03|lock' | tail -15") or "(aucun)")
    print(sh("journalctl --user -u n8n-worker --no-pager --since '-3 min' 2>&1 | "
             "grep -iE 'deadlock|lock timeout|could not obtain|database is locked|SQLITE_BUSY|40P01|55P03|lock' | tail -15") or "(aucun)")
    print("--- attentes de lock actives dans Postgres ---")
    print(psql("SELECT count(*) FROM pg_stat_activity WHERE wait_event_type='Lock';") or "0")

    # 7. cleanup (enfants d'abord, AVANT la suppression du workflow qui cascade execution_entity)
    print("\n--- cleanup ---")
    api("POST", f"/{wid}/deactivate", {})
    psql(f'DELETE FROM execution_data WHERE "executionId" IN (SELECT id FROM execution_entity WHERE "workflowId"=\'{wid}\');')
    psql(f'DELETE FROM execution_entity WHERE "workflowId"=\'{wid}\';')
    api("DELETE", f"/{wid}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
