import json, urllib.request, os

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
H = {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"}
base = "http://localhost:5678/api/v1/workflows"

req = urllib.request.Request(base, headers=H)
d = json.load(urllib.request.urlopen(req, timeout=15))
wfs = d.get("data", [])
print(f"total: {len(wfs)} workflows")
print()
for w in sorted(wfs, key=lambda x: (x.get("active", False), x.get("name", ""))):
    print(f"  [{'ACTIF' if w.get('active') else 'inactif'}] {w.get('name')}  (id={w.get('id')})")
