#!/usr/bin/env python3
"""Diagnostic jetable : runData réel de l'exécution 3121 (base SQLite n8n) + comparaison node Telegram prod."""
import json
import os
import sqlite3
import zlib
import urllib.request

DB = os.path.expanduser("~/.n8n/database.sqlite")
print("=== base n8n:", DB, "===")
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()


def decode_blob(raw):
    """json brut, zlib, ou format n8n « référencé » ([schema, valeurs])."""
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "ignore")
    s = raw.strip()
    doc = None
    if s.startswith("{") or s.startswith("["):
        try:
            doc = json.loads(s)
        except Exception:
            pass
    if doc is None:
        for enc in (s.encode(), bytes.fromhex(s)):
            try:
                doc = json.loads(zlib.decompress(enc).decode("utf-8"))
                break
            except Exception:
                continue
    if doc is None:
        return None
    # format référencé n8n : tableau PLAT — doc[0] = schéma (index en
    # strings), doc[1..n] = valeurs indexées 1..n (doc[1] = startData {}, etc.)
    if isinstance(doc, list) and len(doc) >= 2 and isinstance(doc[0], dict):

        def resolve(v, depth=0):
            if depth > 20:
                return v
            if isinstance(v, str) and v.isdigit():
                i = int(v)
                if 0 < i < len(doc):  # i=0 = le schéma lui-même (à ne pas résoudre)
                    return resolve(doc[i], depth + 1)
            if isinstance(v, dict):
                return {k: resolve(x, depth) for k, x in v.items()}
            if isinstance(v, list):
                return [resolve(x, depth) for x in v]
            return v

        doc = resolve(doc[0])
    return doc


# --- 1) tables + colonnes réelles ---
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%execution%'")
tables = [r[0] for r in cur.fetchall()]
print("tables:", tables)
found = False
for t in tables:
    if "workflow" in t or "annotation" in t or "test" in t or "agent" in t:
        continue
    cur.execute(f"PRAGMA table_info({t})")
    cols = [r[1] for r in cur.fetchall()]
    print(f"\ntable {t}: colonnes = {cols}")
    id_col = "executionId" if "executionId" in cols else ("id" if "id" in cols else None)
    data_col = "data" if "data" in cols else None
    if not id_col or not data_col:
        continue
    cur.execute(f"SELECT {id_col}, {data_col} FROM {t} WHERE {id_col}=3121")
    row = cur.fetchone()
    if not row:
        print("  execution 3121 absente")
        continue
    found = True
    raw = row[1]
    data = decode_blob(raw)
    if not isinstance(data, dict):
        print("  data non décodable:", type(raw), str(raw)[:120])
        continue
    print(f"  clés data: {list(data.keys())[:12]}")
    rd = data.get("resultData", {}).get("runData") or data.get("runData") or {}
    if not rd:
        print("  (runData introuvable)")
        continue
    for node_name, runs in rd.items():
        for run in runs:
            err = run.get("error")
            out = (run.get("data") or {}).get("main", [[]])[0] if run.get("data") else []
            print(f"  node: {node_name} | items: {len(out)} | error: {str(err)[:300] if err else None}")
            for item in out[:2]:
                j = item.get("json", {})
                print("    json:", json.dumps(j, ensure_ascii=False)[:250])
    break
con.close()
if not found:
    print("\n(execution 3121 introuvable dans la base — données purgées ou autre base)")

# --- 2) workflow Equity Alert : nom réel + structure options des nodes http ---
KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
H = {"X-N8N-API-KEY": KEY}
BASE = "http://localhost:5678/api/v1"
req = urllib.request.Request(BASE + "/workflows?limit=100", headers=H)
wfs = json.load(urllib.request.urlopen(req, timeout=20)).get("data", [])
print("\n=== workflows contenant 'equity' (insensible casse) ===")
cands = [w for w in wfs if "equity" in w["name"].lower()]
for w in cands[:6]:
    print(" -", w["name"], f"(id={w['id']}, {'ACTIF' if w.get('active') else 'inactif'})")
if cands:
    d = json.load(urllib.request.urlopen(urllib.request.Request(BASE + f"/workflows/{cands[0]['id']}", headers=H), timeout=20))
    print("types de nodes:", sorted({n.get("type") for n in d.get("nodes", [])}))
    for n in d.get("nodes", []):
        if n.get("type") in ("n8n-nodes-base.httpRequest", "n8n-nodes-base.telegram"):
            p = n.get("parameters", {})
            print("\nnode:", n["name"], "|", n.get("type"))
            print("  options:", json.dumps(p.get("options", {}), ensure_ascii=False))
            if n.get("type") == "n8n-nodes-base.httpRequest":
                print("  sendBody:", p.get("sendBody"), "| specifyBody:", p.get("specifyBody"))
