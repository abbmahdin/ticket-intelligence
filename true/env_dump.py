import json, urllib.request

KEY = open("/home/redou/.quantlive-secrets-backup/.n8n_api_key_found").read().strip()
BASE = "http://localhost:5678/api/v1"
req = urllib.request.Request(f"{BASE}/variables", headers={"X-N8N-API-KEY": KEY})
d = json.load(urllib.request.urlopen(req))
print("=== n8n VARIABLES ===")
for v in d.get("data", []):
    print(f"  {v['key']} = {v['value']}")
