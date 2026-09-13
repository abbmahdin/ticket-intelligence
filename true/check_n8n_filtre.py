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
        return {"__error__": e.code}


full = api("GET", "/workflows/40923f26-db12-4ae8-9061-9becfc27942e")
for n in full.get("nodes", []):
    if n.get("type") == "n8n-nodes-base.code":
        js = n.get("parameters", {}).get("jsCode", "")
        print(f"=== [{n.get('name')}] {len(js)} chars ===")
        print(js)
        print()
