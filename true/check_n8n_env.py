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


# 1) Tracker TP/SL: node HTTP complet (cle Twelve Data ?)
print("=== TRACKER TP/SL - node HTTP Twelve Data ===")
full = api("GET", "/workflows/0f42de21-4419-4c2d-825a-6a720a37c94c")
for n in full.get("nodes", []):
    if n.get("type") == "n8n-nodes-base.httpRequest":
        print(json.dumps(n.get("parameters", {}), ensure_ascii=False, indent=1))
print()

# 2) Env du process n8n (les workflows utilisent $env.TELEGRAM_CHAT_ID, ECON_CALENDAR_URL...)
print("=== ENV process n8n (variables utilisees par les workflows) ===")
import subprocess
pid = subprocess.run(["pgrep", "-f", "n8n"], capture_output=True, text=True).stdout.strip().split("\n")
print("pids n8n:", pid[:5])
if pid and pid[0]:
    try:
        env = open(f"/proc/{pid[0].strip()}/environ").read().split("\0")
        wanted = [k for k in env if any(x in k for x in ("TELEGRAM", "ECON", "CHAT", "GSHEET", "TWELVE", "DATABASE", "SOURCE_HEARTBEAT"))]
        for w in sorted(wanted):
            k, _, v = w.partition("=")
            print(f"  {k}={v[:40]}{'...' if len(v) > 40 else ''}")
    except Exception as e:
        print("  env illisible:", e)
