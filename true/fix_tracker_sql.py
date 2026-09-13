import json, urllib.request, os, sys

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
H = {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"}
BASE = "http://localhost:5678/api/v1"
WF = "0f42de21-4419-4c2d-825a-6a720a37c94c"


def api(method, path, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=H)
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode()[:250]}


# Requetes corrigees -> tables reelles (signals + outcomes), vocabulaire app
Q_OPEN = "SELECT id, symbol, direction, entry_price AS entry, take_profit_1 AS tp, stop_loss AS sl FROM signals WHERE status IN ('active','entered','tp1_hit');"
Q_MAJ = (
    "INSERT INTO outcomes (signal_id, result, exit_price, pnl_pips, source) "
    "VALUES ({{ $json.id }}::bigint, "
    "CASE WHEN '{{ $json.outcome }}' = 'TP' THEN 'tp1_hit' ELSE 'sl_hit' END, "
    "{{ $json.price }}::numeric, {{ $json.pnl }}::numeric, 'n8n_tracker') "
    "ON CONFLICT (signal_id) DO NOTHING;"
)

full = api("GET", f"/workflows/{WF}")
if "__error__" in full:
    print("ECHEC GET:", full["__error__"])
    sys.exit(1)

updates = 0
for n in full.get("nodes", []):
    if n.get("type") != "n8n-nodes-base.postgres":
        continue
    name = n.get("name", "")
    q = (n.get("parameters", {}) or {}).get("query", "")
    if "Trades Ouverts" in name or "quantlive_trades" in q and "SELECT" in q:
        n["parameters"]["query"] = Q_OPEN
        updates += 1
        print(f"  requete corrigee: {name} (SELECT)")
    elif "MAJ" in name or "quantlive_trades" in q and "UPDATE" in q:
        n["parameters"]["query"] = Q_MAJ
        updates += 1
        print(f"  requete corrigee: {name} (INSERT outcomes)")

print(f"Nodes postgres corriges: {updates}")
if updates != 2:
    print("ERREUR: 2 nodes postgres attendus, echec du matching (nodes renommes ?)")
    sys.exit(1)

if updates > 0:
    payload = {
        k: full[k]
        for k in ("name", "nodes", "connections", "settings", "staticData", "pinData")
        if k in full
    }
    res = api("PUT", f"/workflows/{WF}", payload)
    if "__error__" in res:
        print("ECHEC PUT:", res["__error__"], res.get("__body__", ""))
        sys.exit(1)
    print("PUT OK")

# Verification
full2 = api("GET", f"/workflows/{WF}")
print("\n=== Requetes finales ===")
for n in full2.get("nodes", []):
    if n.get("type") == "n8n-nodes-base.postgres":
        print(f"--- [{n.get('name')}] ---")
        print((n.get("parameters", {}) or {}).get("query", ""))
