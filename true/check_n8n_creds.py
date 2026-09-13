import json, urllib.request, os, sys

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
H = {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"}
BASE = "http://localhost:5678/api/v1"


def api(method, path, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=H)
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode()[:200]}


# --- credentials existantes ---
creds = api("GET", "/credentials?limit=100")
existing = {}
for c in creds.get("data", []):
    existing[c["id"]] = c.get("name", "?")
print(f"=== Credentials existantes dans n8n : {len(existing)} ===")
for cid, name in sorted(existing.items(), key=lambda x: x[1]):
    print(f"  {cid}  ->  {name}")
print()

# --- workflows inactifs ---
wfs = api("GET", "/workflows?limit=100")
all_wfs = wfs.get("data", [])
inactive = [w for w in all_wfs if not w.get("active")]
print(f"=== Workflows inactifs : {len(inactive)} / {len(all_wfs)} ===")
print()

results = []
for w in sorted(inactive, key=lambda x: x.get("name", "")):
    full = api("GET", f"/workflows/{w['id']}")
    nodes = full.get("nodes", [])
    refs = []
    for n in nodes:
        cred = n.get("credentials") or {}
        for cname, cinfo in cred.items():
            if isinstance(cinfo, dict):
                cid = cinfo.get("id")
                cref_name = cinfo.get("name")
                refs.append((cname, cid, cref_name))
    missing = [r for r in refs if r[1] and r[1] not in existing]
    ok = len(missing) == 0
    status = "OK (credits valides)" if ok else f"MANQUANT: {missing}"
    results.append((ok, w.get("name", "?"), w["id"], status))
    print(f"[{'OK ' if ok else 'XX '}] {w.get('name', '?')}  (id={w['id']})")
    for cname, cid, cref_name in refs:
        state = "existe" if (not cid or cid in existing) else "*** MANQUANTE ***"
        print(f"        node cred {cname!r}: id={cid} name={cref_name!r} -> {state}")
    if not refs:
        print("        (aucune credential referencee)")

print()
ok_count = sum(1 for r in results if r[0])
print(f"=== BILAN : {ok_count} workflows activables / {len(results)} inactifs ===")
