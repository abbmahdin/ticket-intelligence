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


TARGETS = {
    "7ac76424-e981-4415-948e-956a0044a286": "Signal Router XAUUSD",
    "40923f26-db12-4ae8-9061-9becfc27942e": "Filtre News Haut Impact",
    "767d3671-5949-47da-845a-684e3a2f57d5": "Watchdog Source Signaux",
}

for wid, name in TARGETS.items():
    full = api("GET", f"/workflows/{wid}")
    if "__error__" in full:
        print(f"== {name}: ERROR {full['__error__']}")
        continue
    print(f"== {name} (active={full.get('active')}) ==")
    nodes = full.get("nodes", [])
    print(f"   {len(nodes)} nodes")
    for n in nodes:
        t = n.get("type", "")
        nm = n.get("name", "?")
        params = n.get("parameters", {})
        # Resume
        summary = []
        if "Trigger" in t or t.endswith("Webhook"):
            summary.append(f"TRIGGER/WEBHOOK: {t}")
        if "dedup" in json.dumps(params).lower() or "processed" in json.dumps(params).lower():
            summary.append("dedup/processed mention")
        if "telegram" in t.lower():
            summary.append(f"TELEGRAM SEND: chatId={params.get('chatId', params.get('chatIds', '?'))}")
        if "httpRequest" in t:
            summary.append(f"HTTP: {params.get('url', params.get('method', '?'))}")
        print(f"   - {nm} [{t}] {' | '.join(summary)}")
    print()
