import json, urllib.request, sys

KEY = open("/home/redou/.quantlive-secrets-backup/.n8n_api_key_found").read().strip()
BASE = "http://localhost:5678/api/v1"
req = urllib.request.Request(f"{BASE}/workflows", headers={"X-N8N-API-KEY": KEY})
data = json.load(urllib.request.urlopen(req))["data"]

ids = sys.argv[1:]
for wid in ids:
    wf = next((w for w in data if w["id"] == wid), None)
    if not wf:
        print(f"NOT FOUND: {wid}"); continue
    print("="*72)
    print(f"WF={wf['name']} ({wid})")
    for n in wf["nodes"]:
        if "Trigger" in n["type"]:
            continue
        if n["type"] == "n8n-nodes-base.webhook":
            continue
        s = json.dumps(n.get("parameters", {}), ensure_ascii=False)
        print(f"\n### {n['name']} [{n['type']}]")
        print(s[:1200])
