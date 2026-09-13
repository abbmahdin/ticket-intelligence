import json, urllib.request, os

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
H = {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"}
BASE = "http://localhost:5678/api/v1"


def api(method, path, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=H)
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode()[:150]}


TARGETS = {
    "90512876-6828-4481-b9de-da7c92bc1075": "Brief Matinal XAUUSD",
    "40923f26-db12-4ae8-9061-9becfc27942e": "Filtre News Haut Impact",
    "0f42de21-4419-4c2d-825a-6a720a37c94c": "Tracker TP/SL Temps Reel",
    "addon_quantlive_equity_curve": "Equity Alert Bot",
    "0e6f5ad8-a5b9-4ed8-afe8-4528c002454d": "Gestion Bankroll & Stakes",
}

for wid, name in TARGETS.items():
    full = api("GET", f"/workflows/{wid}")
    if "__error__" in full:
        print(f"== {name}: ERROR {full['__error__']} {full.get('__body__','')}")
        continue
    print(f"== {name} (active={full.get('active')}) ==")
    nodes = full.get("nodes", [])
    connections = full.get("connections", {})
    print(f"   nodes: {len(nodes)}")
    for n in nodes:
        t = n.get("type", "")
        p = n.get("parameters", {})
        creds = n.get("credentials") or {}
        cred_str = ", ".join(f"{k}={v.get('id')}({v.get('name')})" for k, v in creds.items()) or "aucune"
        # Resume params significatifs
        ps = {}
        for k in ("path", "httpMethod", "url", "method", "chatId", "chatIds",
                  "operation", "resource", "table", "schema", "database", "host",
                  "mode", "function", "column", "documentId"):
            if k in p:
                v = p[k]
                ps[k] = str(v)[:80]
        print(f"   - {n.get('name')} [{t}]")
        print(f"       creds: {cred_str}")
        if ps:
            print(f"       params: {json.dumps(ps, ensure_ascii=False)}")
        # Code nodes
        if t == "n8n-nodes-base.code" and "jsCode" in p:
            print(f"       code({len(p['jsCode'])}c): {p['jsCode'][:200].replace(chr(10),' ')}")
    print()
