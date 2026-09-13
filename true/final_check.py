import json, urllib.request, os, subprocess

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
H = {"X-N8N-API-KEY": KEY}
BASE = "http://localhost:5678/api/v1"

# 1) py_compile de tous les scripts crees
print("=== py_compile scripts ===")
scripts = [
    "list_n8n_wf.py", "check_n8n_creds.py", "check_n8n_triggers.py",
    "activate_n8n_ok.py", "check_n8n_after.py", "check_n8n_nodes_raw.py",
    "check_n8n_webhook.py", "check_n8n_filtre.py", "check_n8n_env.py",
    "check_n8n_svc.py", "create_n8n_pg_cred.py", "activate_tracker.py",
    "deactivate_watchdog.py", "relink_bankroll_tg2.py", "check_n8n_state2.py",
    "dump_tracker.py", "fix_tracker_sql.py", "build_drift_alert.py",
    "patch_drift_threshold.py", "final_check.py",
]
r = subprocess.run(["python3", "-m", "py_compile"] + scripts, capture_output=True, text=True)
print("py_compile:", "OK" if r.returncode == 0 else r.stderr[:300])

# 2) Etat des workflows cles
print("\n=== Etat workflows cles ===")
wfs = api = None
req = urllib.request.Request(f"{BASE}/workflows?limit=100", headers=H)
wfs = json.load(urllib.request.urlopen(req, timeout=15)).get("data", [])

keys = {
    "0f42de21-4419-4c2d-825a-6a720a37c94c": "Tracker TP/SL Temps Reel",
    "HR1tZTFQRIEPKbrB": "Drift Alert",
    "90512876-6828-4481-b9de-da7c92bc1075": "Brief Matinal",
    "40923f26-db12-4ae8-9061-9becfc27942e": "Filtre News",
    "767d3671-5949-47da-845a-684e3a2f57d5": "Watchdog (desactive)",
    "addon_quantlive_equity_curve": "Equity Alert (attente Sheets)",
    "0e6f5ad8-a5b9-4ed8-afe8-4528c002454d": "Gestion Bankroll (attente Sheets)",
}
for wid, label in keys.items():
    w = next((x for x in wfs if x["id"] == wid), None)
    if w:
        print(f"  [{'ACTIF' if w.get('active') else 'inactif'}] {label}")

# 3) Total
act = sum(1 for w in wfs if w.get("active"))
print(f"\n=== Total workflows actifs : {act} / {len(wfs)} ===")
