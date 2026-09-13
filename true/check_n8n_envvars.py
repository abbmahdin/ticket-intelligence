import json, urllib.request, os

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
H = {"X-N8N-API-KEY": KEY}
BASE = "http://localhost:5678/api/v1"


def api(method, path, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=H)
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"__error__": e.code}


# 1) Workflow Watchdog : code node pour comprendre SOURCE_HEARTBEAT_URL
print("=== WATCHDOG - code node Analyser Heartbeat ===")
full = api("GET", "/workflows/767d3671-5949-47da-845a-684e3a2f57d5")
for n in full.get("nodes", []):
    if n.get("type") == "n8n-nodes-base.code":
        js = n.get("parameters", {}).get("jsCode", "")
        print(js[:900])
print()

# 2) Toutes les $env.X utilisees par les workflows ACTIFS (scan)
print("=== Variables $env utilisees par les workflows ===")
wfs = api("GET", "/workflows?limit=100").get("data", [])
envs = set()
for w in wfs:
    full = api("GET", f"/workflows/{w['id']}")
    for n in full.get("nodes", []):
        s = json.dumps(n.get("parameters", {}))
        import re
        for m in re.finditer(r"\$env\.([A-Z_0-9]+)", s):
            envs.add(m.group(1))
for e in sorted(envs):
    print("  ", e)
