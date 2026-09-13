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


# 1) Webhook path du Signal Router XAUUSD vs router actif
print("=== WEBHOOK PATHS ===")
wfs = api("GET", "/workflows?limit=100").get("data", [])
for w in wfs:
    nm = w.get("name", "")
    if "Router" in nm or "Routeur" in nm or "Signal Router" in nm:
        full = api("GET", f"/workflows/{w['id']}")
        if "__error__" in full:
            continue
        for n in full.get("nodes", []):
            if n.get("type") == "n8n-nodes-base.webhook":
                p = n.get("parameters", {})
                print(f"  {nm} (active={full.get('active')}): path={p.get('path')!r} method={p.get('httpMethod')} respMode={p.get('responseMode')}")
        # pour Signal Router, afficher le path webhook specifique
        if "Signal Router" in nm:
            for n in full.get("nodes", []):
                if n.get("type") == "n8n-nodes-base.webhook":
                    p = n.get("parameters", {})
                    print(f"    -> path: {p.get('path')!r}")

print()
# 2) Filtre News : code node dedup ?
print("=== FILTRE NEWS - contenu du code node (dedup?) ===")
full = api("GET", "/workflows/40923f26-db12-4ae8-9061-9becfc27942e")
for n in full.get("nodes", []):
    if n.get("type") == "n8n-nodes-base.code":
        js = n.get("parameters", {}).get("jsCode", "")
        if len(js) > 400:
            print(f"  [{n.get('name')}] code {len(js)} chars, debut:")
            print("    " + js[:400].replace("\n", "\n    "))
            print("    ...")
            if "dedup" in js.lower() or "already" in js.lower() or "seen" in js.lower() or "memory" in js.lower() or "item" in js.lower():
                print(f"    -> mots-cles dedup trouves: {[k for k in ['dedup','already','seen','memory'] if k in js.lower()]}")
            else:
                print("    -> AUCUN mot-cle dedup evidemment detecte")
        else:
            print(f"  [{n.get('name')}] code court: {js[:300]}")
