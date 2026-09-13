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


# Workflows concernes par l'activation
TARGETS = {
    "90512876-6828-4481-b9de-da7c92bc1075": "Brief Matinal XAUUSD",
    "ldmRadrkOX6obEN6": "Concordia - Test Node",
    "40923f26-db12-4ae8-9061-9becfc27942e": "Filtre News Haut Impact",
    "7ac76424-e981-4415-948e-956a0044a286": "Signal Router XAUUSD",
    "767d3671-5949-47da-845a-684e3a2f57d5": "Watchdog Source Signaux",
}

print("=== Etat final + details trigger des workflows planifies ===")
for wid, name in TARGETS.items():
    full = api("GET", f"/workflows/{wid}")
    if "__error__" in full:
        print(f"  {name}: ERROR {full['__error__']}")
        continue
    active = full.get("active")
    print(f"\n  {name} -> active={active}")
    for n in full.get("nodes", []):
        t = n.get("type", "")
        if "Trigger" in t or t.endswith("Webhook"):
            p = n.get("parameters", {})
            rule = p.get("rule", {})
            print(f"    trigger {n.get('name')}: type={t}")
            print(f"      parameters: {json.dumps(p, ensure_ascii=False)[:400]}")

print()
print("=== Verification globale: comptage actifs/inactifs ===")
wfs = api("GET", "/workflows?limit=100").get("data", [])
act = sum(1 for w in wfs if w.get("active"))
print(f"  actifs: {act} / {len(wfs)}")
for w in sorted(wfs, key=lambda x: x.get("name", "")):
    if not w.get("active"):
        print(f"    [inactif] {w.get('name')}")
