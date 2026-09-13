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


# Watchdog Source Signaux : SOURCE_HEARTBEAT_URL non definie -> desactivation propre
WF = "767d3671-5949-47da-845a-684e3a2f57d5"
res = api("POST", f"/workflows/{WF}/deactivate")
if "__error__" in res:
    print("ECHEC:", res["__error__"], res.get("__body__", ""))
else:
    print("Watchdog Source Signaux -> active =", res.get("active"))

# Etat global
wfs = api("GET", "/workflows?limit=100").get("data", [])
act = sum(1 for w in wfs if w.get("active"))
print(f"Total workflows actifs : {act} / {len(wfs)}")
