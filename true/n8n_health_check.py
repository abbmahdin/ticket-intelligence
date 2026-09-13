import json, os, urllib.request
from collections import defaultdict

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
H = {"X-N8N-API-KEY": KEY}
BASE = "http://localhost:5678/api/v1"

def api(path, timeout=20):
    req = urllib.request.Request(BASE + path, headers=H)
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode()[:300]}

# 1) workflows
wfs = api("/workflows?limit=250")
wflist = wfs.get("data", []) if isinstance(wfs.get("data"), list) else wfs.get("data", {}).get("results", [])
wfname = {w["id"]: w.get("name") for w in wflist}
wfactive = {w["id"]: w.get("active") for w in wflist}
print(f"workflows: {len(wflist)} (actifs: {sum(1 for w in wflist if w.get('active'))})")

# 2) executions en erreur / crash
errors = []
for status in ("error", "crashed"):
    r = api(f"/executions?status={status}&limit=250")
    data = r.get("data", [])
    if isinstance(data, dict):
        data = data.get("results", data.get("executions", []))
    errors.extend(data)
print(f"executions en erreur/crash (recuperees): {len(errors)}")

# 3) grouper par workflow
by_wf = defaultdict(list)
for e in errors:
    by_wf[e.get("workflowId")].append(e)

print("\n=== Erreurs par workflow ===")
for wid, es in sorted(by_wf.items(), key=lambda kv: -len(kv[1])):
    name = wfname.get(wid, wid)
    print(f"  {len(es):>3}  {name}  (active={wfactive.get(wid)})")

# 4) échantillonner le message d'erreur (dernier en date)
print("\n=== Detail (derniere execution en erreur de chaque workflow) ===")
for wid, es in sorted(by_wf.items(), key=lambda kv: -len(kv[1])):
    name = wfname.get(wid, wid)
    e = es[0]  # plus recent (ordre desc)
    eid = e.get("id")
    d = api(f"/executions/{eid}?includeData=true")
    rd = d.get("data", {}).get("resultData", {})
    wf_err = rd.get("error")
    msg = ""
    if isinstance(wf_err, dict):
        msg = wf_err.get("message", "")
    elif isinstance(wf_err, str):
        msg = wf_err
    if not msg:
        # chercher l'erreur au niveau des nodes
        for nname, runs in (rd.get("runData") or {}).items():
            for run in runs:
                if run.get("error"):
                    e2 = run["error"]
                    msg = (e2.get("message") if isinstance(e2, dict) else str(e2)) or ""
                    msg = f"[node:{nname}] {msg}"
                    break
            if msg:
                break
    print(f"\n--- {name} (exec {eid}, {e.get('status')}) ---")
    print(f"    {msg[:400]}")
