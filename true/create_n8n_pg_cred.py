import json, urllib.request, os, re, sys

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
H = {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"}
BASE = "http://localhost:5678/api/v1"


def api(method, path, body=None, timeout=25):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=H)
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode()[:250]}


# --- 1) Parse DATABASE_URL depuis .env QuantLive ---
env_path = "/home/redou/QuantLive/.env"
m = None
for line in open(env_path):
    if line.startswith("DATABASE_URL="):
        m = line.strip().split("=", 1)[1].strip().strip('"')
        break
if not m:
    print("DATABASE_URL introuvable")
    sys.exit(1)

# postgresql+asyncpg://user:pass@host:port/db
m2 = re.match(r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@([^:/]+):(\d+)/(\w+)", m)
if not m2:
    print("URL non parseable:", m[:60])
    sys.exit(1)
user, pwd, host, port, db = m2.groups()
print(f"DB: host={host} port={port} db={db} user={user} (mdp masque)")

# --- 2) Creer la credential postgres si elle n'existe pas ---
existing = api("GET", "/credentials?limit=100")
cred_id = None
for c in existing.get("data", []):
    if c.get("type") == "postgres" and "QuantLive" in c.get("name", ""):
        cred_id = c["id"]
        print("Credential Postgres deja presente:", cred_id)
        break

if not cred_id:
    body = {
        "name": "QuantLive Postgres",
        "type": "postgres",
        "data": {
            "host": host,
            "port": int(port),
            "database": db,
            "user": user,
            "password": pwd,
            "ssl": "disable",
            "allowUnauthorizedCerts": False,
        },
    }
    res = api("POST", "/credentials", body)
    if "__error__" in res:
        print("ECHEC creation credential:", res["__error__"], res.get("__body__", ""))
        sys.exit(1)
    cred_id = res["id"]
    print("Credential Postgres creee:", cred_id)

# --- 3) Relier les 2 nodes postgres du Tracker TP/SL (REPLACE -> cred_id) ---
WF_TRACKER = "0f42de21-4419-4c2d-825a-6a720a37c94c"
full = api("GET", f"/workflows/{WF_TRACKER}")
if "__error__" in full:
    print("ECHEC GET workflow tracker:", full["__error__"])
    sys.exit(1)

changed = 0
for n in full.get("nodes", []):
    creds = n.get("credentials") or {}
    for cname, cinfo in creds.items():
        if isinstance(cinfo, dict) and cinfo.get("id") == "REPLACE" and cinfo.get("name") == "Postgres":
            cinfo["id"] = cred_id
            cinfo["name"] = "QuantLive Postgres"
            changed += 1

if changed == 0:
    print("Aucun node postgres REPLACE trouve (deja relie?)")
else:
    # PUT n'accepte qu'un sous-ensemble de proprietes (meta et tags sont readOnly)
    payload = {
        k: full[k]
        for k in ("name", "nodes", "connections", "settings", "staticData", "pinData")
        if k in full
    }
    res = api("PUT", f"/workflows/{WF_TRACKER}", payload)
    if "__error__" in res:
        print("ECHEC PUT workflow:", res["__error__"], res.get("__body__", ""))
        sys.exit(1)
    print(f"Workflow Tracker mis a jour: {changed} node(s) postgres relie(s) a {cred_id}")

# --- 4) Verif finale ---
full2 = api("GET", f"/workflows/{WF_TRACKER}")
for n in full2.get("nodes", []):
    creds = n.get("credentials") or {}
    for cname, cinfo in creds.items():
        print(f"  node [{n.get('name')}] cred {cname} -> id={cinfo.get('id')} name={cinfo.get('name')}")
