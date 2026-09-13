import json, urllib.request, os

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
H = {"X-N8N-API-KEY": KEY}
BASE = "http://localhost:5678/api/v1"

def api(path):
    req = urllib.request.Request(BASE + path, headers=H)
    return json.load(urllib.request.urlopen(req, timeout=20))

w = api("/workflows/quantlive_ops_tradingview_inbound")
print("=== WORKFLOW:", w.get("name"), "| active =", w.get("active"), "===")
print("settings:", json.dumps(w.get("settings", {}), indent=2)[:1500])
print()

for n in w.get("nodes", []):
    print("-" * 80)
    print(f"NODE: {n.get('name')}  (type={n.get('type')})")
    p = n.get("parameters", {})
    if n.get("type", "").startswith("n8n-nodes-base.webhook"):
        print("  httpMethod:", p.get("httpMethod"))
        print("  path:", p.get("path"))
        print("  responseMode:", p.get("responseMode"))
        print("  options:", json.dumps(p.get("options", {})))
        hdrs = p.get("headerParameters", {})
        print("  headerParameters:", json.dumps(hdrs, indent=2)[:1500])
    if n.get("type", "").startswith("n8n-nodes-base.code") or n.get("type", "") == "n8n-nodes-base.function":
        js = p.get("jsCode", "")
        print("  jsCode (full):")
        print(js)
    # print all params for other nodes briefly
    other = {k: v for k, v in p.items() if k not in ("jsCode", "headerParameters")}
    if other and not n.get("type", "").startswith("n8n-nodes-base.webhook"):
        s = json.dumps(other)
        print("  params:", s[:800])
