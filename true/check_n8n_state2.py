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


# 1) Credentials actuelles
print("=== Credentials n8n actuelles ===")
creds = api("GET", "/credentials?limit=100")
for c in creds.get("data", []):
    print(f"  {c['id']} -> {c.get('name')} ({c.get('type')})")

# 2) Etat des 5 workflows prioritaires
TARGETS = {
    "90512876-6828-4481-b9de-da7c92bc1075": "Brief Matinal XAUUSD",
    "40923f26-db12-4ae8-9061-9becfc27942e": "Filtre News Haut Impact",
    "0f42de21-4419-4c2d-825a-6a720a37c94c": "Tracker TP/SL Temps Reel",
    "addon_quantlive_equity_curve": "Equity Alert Bot",
    "0e6f5ad8-a5b9-4ed8-afe8-4528c002454d": "Gestion Bankroll & Stakes",
}
print()
print("=== Etat des 5 workflows prioritaires ===")
for wid, name in TARGETS.items():
    full = api("GET", f"/workflows/{wid}")
    if "__error__" in full:
        print(f"  {name}: ERROR {full['__error__']}")
        continue
    creds_used = set()
    for n in full.get("nodes", []):
        for cname, cinfo in (n.get("credentials") or {}).items():
            if isinstance(cinfo, dict):
                creds_used.add(f"{cname}={cinfo.get('id')}({cinfo.get('name')})")
    print(f"  [{'ACTIF' if full.get('active') else 'inactif'}] {name}")
    for cu in sorted(creds_used):
        print(f"       cred: {cu}")

# 3) Total
wfs = api("GET", "/workflows?limit=100").get("data", [])
act = sum(1 for w in wfs if w.get("active"))
print()
print(f"Total workflows actifs : {act} / {len(wfs)}")
