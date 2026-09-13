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
        return {"__error__": e.code, "__body__": e.read().decode()[:200]}


# 5 candidats avec credentials valides (Telegram Bot reel) ou sans trigger actif.
# EXCLU : quantlivecal01 (Economic Calendar) -> doublon de l'actif id=1.
CANDIDATES = {
    "90512876-6828-4481-b9de-da7c92bc1075": "Brief Matinal XAUUSD",
    "ldmRadrkOX6obEN6": "Concordia - Test Node",
    "40923f26-db12-4ae8-9061-9becfc27942e": "Filtre News Haut Impact",
    "7ac76424-e981-4415-948e-956a0044a286": "Signal Router XAUUSD",
    "767d3671-5949-47da-845a-684e3a2f57d5": "Watchdog Source Signaux",
}

ok, fail = 0, 0
for wid, name in CANDIDATES.items():
    res = api("POST", f"/workflows/{wid}/activate")
    if "__error__" in res:
        fail += 1
        print(f"  ECHEC: {name} -> {res['__error__']} {res.get('__body__', '')[:120]}")
    else:
        ok += 1
        print(f"  ACTIVE: {name} (active={res.get('active')})")

print(f"\n=== BILAN : {ok} active(s), {fail} echec(s) ===")
