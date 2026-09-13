import json, urllib.request, os, subprocess

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


# 1) Env du process n8n : cles chargees ?
print("=== ENV process n8n (nouvelles cles) ===")
out = subprocess.run(["systemctl", "--user", "show", "n8n.service", "-p", "MainPID", "--value"],
                     capture_output=True, text=True).stdout.strip()
print("MainPID:", out)
try:
    env = open(f"/proc/{out}/environ").read().split("\0")
    for e in env:
        if e.startswith(("TWELVE_DATA_API_KEY=", "TELEGRAM_BOT_TOKEN=", "TELEGRAM_CHAT_ID=")):
            k, _, v = e.partition("=")
            print(f"  {k}={'<set>' if v else '<VIDE>'}")
except Exception as ex:
    print("  env illisible:", ex)

# 2) Activer le Tracker TP/SL Temps Reel
print()
print("=== Activation Tracker TP/SL Temps Reel ===")
WF = "0f42de21-4419-4c2d-825a-6a720a37c94c"
res = api("POST", f"/workflows/{WF}/activate")
if "__error__" in res:
    print("ECHEC:", res["__error__"], res.get("__body__", ""))
else:
    print("ACTIVE:", res.get("active"))

# 3) Etat final
full = api("GET", f"/workflows/{WF}")
print()
print("=== Etat final Tracker ===")
print("active =", full.get("active"))
for n in full.get("nodes", []):
    t = n.get("type", "")
    trig = "TRIGGER" if ("Trigger" in t or t.endswith("Webhook")) else ""
    print(f"  - {n.get('name')} [{t}] {trig}")

# 4) Comptage global
wfs = api("GET", "/workflows?limit=100").get("data", [])
act = sum(1 for w in wfs if w.get("active"))
print()
print(f"=== Total workflows actifs : {act} / {len(wfs)} ===")
