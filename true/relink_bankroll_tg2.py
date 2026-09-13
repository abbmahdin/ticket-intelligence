import json, urllib.request, os

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
H = {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"}
BASE = "http://localhost:5678/api/v1"
REAL_TG = "a1cf4abee1304724"


def api(method, path, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=H)
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode()[:200]}


# 1) Trouver le workflow par nom
wfs = api("GET", "/workflows?limit=100").get("data", [])
target = None
for w in wfs:
    if "Gestion Bankroll" in w.get("name", ""):
        target = w
        break
if not target:
    print("Workflow 'Gestion Bankroll' introuvable")
    print("Workflows contenant 'Bankroll':", [w.get("name") for w in wfs if "Bankroll" in w.get("name", "")])
    raise SystemExit(1)

WF = target["id"]
print(f"Workflow trouve: {target['name']} (id={WF}) active={target.get('active')}")

# 2) Re-lier la credential Telegram fantome
full = api("GET", f"/workflows/{WF}")
if "__error__" in full:
    print("ECHEC GET:", full["__error__"])
    raise SystemExit(1)

changed = 0
for n in full.get("nodes", []):
    creds = n.get("credentials") or {}
    for cname, cinfo in creds.items():
        if isinstance(cinfo, dict) and cname == "telegramApi" and cinfo.get("id") == "REPLACE":
            cinfo["id"] = REAL_TG
            cinfo["name"] = "Telegram Bot"
            changed += 1

print(f"Nodes telegram a relier: {changed}")

if changed > 0:
    payload = {
        k: full[k]
        for k in ("name", "nodes", "connections", "settings", "staticData", "pinData")
        if k in full
    }
    res = api("PUT", f"/workflows/{WF}", payload)
    if "__error__" in res:
        print("ECHEC PUT:", res["__error__"], res.get("__body__", ""))
        raise SystemExit(1)
    print("PUT OK")

# 3) Verif
full2 = api("GET", f"/workflows/{WF}")
print("Etat final des credentials du workflow:")
for n in full2.get("nodes", []):
    creds = n.get("credentials") or {}
    for cname, cinfo in creds.items():
        print(f"  node [{n.get('name')}] cred {cname} -> id={cinfo.get('id')} name={cinfo.get('name')}")
