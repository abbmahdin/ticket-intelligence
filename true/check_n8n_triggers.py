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


CANDIDATES = {
    "90512876-6828-4481-b9de-da7c92bc1075": "Brief Matinal XAUUSD",
    "ldmRadrkOX6obEN6": "Concordia - Test Node",
    "40923f26-db12-4ae8-9061-9becfc27942e": "Filtre News Haut Impact",
    "quantlivecal01": "Economic Calendar (ForexFactory) - INACTIF",
    "7ac76424-e981-4415-948e-956a0044a286": "Signal Router XAUUSD",
    "767d3671-5949-47da-845a-684e3a2f57d5": "Watchdog Source Signaux",
}

print("=== TRIGGERS des 6 candidats ===")
for wid, name in CANDIDATES.items():
    full = api("GET", f"/workflows/{wid}")
    if "__error__" in full:
        print(f"  {name}: ERROR {full['__error__']}")
        continue
    triggers = []
    for n in full.get("nodes", []):
        t = n.get("type", "")
        if "Trigger" in t or t.endswith("Webhook"):
            params = n.get("parameters", {})
            rules = params.get("rule", {}).get("interval", [{}]) if isinstance(params.get("rule"), dict) else []
            triggers.append((n.get("name"), t.split(".")[-1], params.get("triggerTimes"), params.get("httpMethod")))
    print(f"  {name}:")
    for tr in triggers:
        print(f"      trigger: {tr[0]} ({tr[1]}) times={tr[2]} method={tr[3]}")
    if not triggers:
        print(f"      (aucun trigger trouve)")
    active = full.get("active")
    print(f"      active={active}")
print()

# --- credentials utilisees par les workflows ACTIFS (pour comparer le pattern REPLACE) ---
print("=== Credentials referencees par les workflows ACTIFS (echantillon) ===")
wfs = api("GET", "/workflows?limit=100").get("data", [])
active_wfs = [w for w in wfs if w.get("active")]
seen = set()
for w in sorted(active_wfs, key=lambda x: x.get("name", "")):
    full = api("GET", f"/workflows/{w['id']}")
    for n in full.get("nodes", []):
        for cname, cinfo in (n.get("credentials") or {}).items():
            if isinstance(cinfo, dict):
                key = (cname, cinfo.get("id"))
                if key not in seen:
                    seen.add(key)
                    print(f"  {w.get('name')}: {cname} -> id={cinfo.get('id')} name={cinfo.get('name')}")
