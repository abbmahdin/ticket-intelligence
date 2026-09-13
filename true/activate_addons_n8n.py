import json, urllib.request, os
KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
H = {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"}
base = "http://localhost:5678/api/v1/workflows"

def api(method, path, body=None):
    req = urllib.request.Request(base + path, data=(json.dumps(body).encode() if body is not None else None),
                                 method=method, headers=H)
    return urllib.request.urlopen(req, timeout=15)

d = json.load(api("GET", ""))
wfs = d.get("data", [])
targets = [w for w in wfs if w["name"].startswith("QuantLive") or w["name"].startswith("Cross")]
print("ADDONS a activer:", len(targets))
ok = 0
for w in targets:
    wid = w["id"]
    try:
        full = json.load(api("GET", f"/{wid}"))
        full["active"] = True
        # PUT pour mettre a jour + activer
        req = urllib.request.Request(base + f"/{wid}", data=json.dumps(full).encode(),
                                     method="PUT", headers=H)
        urllib.request.urlopen(req, timeout=15)
        ok += 1
        print("  ACTIVE:", w["name"])
    except Exception as e:
        print("  ECHEC:", w["name"], str(e)[:60])
print("Actives:", ok, "/", len(targets))
