#!/usr/bin/env python3
"""Corrige la notification Telegram du workflow « QuantLive - Breakeven & Trailing MT4 ».

Le nœud « Notif Telegram BE/Trailing » est branché APRÈS le nœud HTTP
« Envoyer modify MT4 » : $json y est donc la RÉPONSE de
/api/mt4/accounts/{name}/modify, qui ne renvoie que {ok, action, account,
ticket, sl, tp} (cf. app/api/mt4_accounts.py). Les champs side/symbol/rule/r/
current_sl/new_sl/price_ref n'existent que dans la sortie du nœud Code
« Breakeven & Trailing » — d'où la notification reçue vide hormis
Compte/Ticket (ex. « Ticket: 1619750818 ( ) / Règle:  à R / SL:  →  »).

Correctif : le texte du nœud Telegram référence l'item apparié du nœud Code
via $('Breakeven & Trailing').item.json.*  (appariement 1:1 conservé par le
nœud HTTP per-item).
"""
import json
import os
import sys
import urllib.request

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
BASE = "http://localhost:5678/api/v1"
H = {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"}

WF_NAME = "QuantLive - Breakeven & Trailing MT4"
NODE_NAME = "Notif Telegram BE/Trailing"

OLD_TEXT = (
    "=🔒 *Breakeven/Trailing MT4*\n"
    "Compte: {{ $json.account }}\n"
    "Ticket: {{ $json.ticket }} ({{ $json.side }} {{ $json.symbol }})\n"
    "Règle: *{{ $json.rule }}* à {{ $json.r }}R\n"
    "SL: {{ $json.current_sl }} → *{{ $json.new_sl }}*\n"
    "Réf: {{ $json.price_ref }}"
)
NEW_TEXT = (
    "=🔒 *Breakeven/Trailing MT4*\n"
    "Compte: {{ $('Breakeven & Trailing').item.json.account }}\n"
    "Ticket: {{ $('Breakeven & Trailing').item.json.ticket }} "
    "({{ $('Breakeven & Trailing').item.json.side }} "
    "{{ $('Breakeven & Trailing').item.json.symbol }})\n"
    "Règle: *{{ $('Breakeven & Trailing').item.json.rule }}* "
    "à {{ $('Breakeven & Trailing').item.json.r }}R\n"
    "SL: {{ $('Breakeven & Trailing').item.json.current_sl }} → "
    "*{{ $('Breakeven & Trailing').item.json.new_sl }}*\n"
    "Réf: {{ $('Breakeven & Trailing').item.json.price_ref }}"
)


def api(method, path, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode()[:400]}


def main():
    wfs = api("GET", "/workflows?limit=100").get("data", [])
    existing = [w for w in wfs if w.get("name") == WF_NAME]
    if not existing:
        print(f"[FAIL] workflow {WF_NAME} introuvable")
        sys.exit(1)
    wid = existing[0]["id"]
    print(f"[EXIST] {WF_NAME} id={wid} active={existing[0].get('active')}")

    wf = api("GET", f"/workflows/{wid}")
    if "__error__" in wf:
        print(f"[FAIL] GET {wf['__error__']} {wf.get('__body__')}")
        sys.exit(1)
    nodes = wf.get("nodes", [])
    target = next((n for n in nodes if n.get("name") == NODE_NAME), None)
    if target is None:
        print(f"[FAIL] nœud {NODE_NAME} introuvable")
        sys.exit(1)
    before = target["parameters"].get("text", "")
    if before == NEW_TEXT:
        print("[OK] texte déjà corrigé, rien à faire")
        return
    target["parameters"]["text"] = NEW_TEXT

    payload = {
        "name": wf.get("name"),
        "nodes": nodes,
        "connections": wf.get("connections"),
        "settings": wf.get("settings"),
    }
    r = api("PUT", f"/workflows/{wid}", payload)
    if "__error__" in r:
        print(f"[FAIL] PUT {r['__error__']} {r.get('__body__')}")
        sys.exit(1)
    print("[PUT] workflow mis à jour")

    act = api("POST", f"/workflows/{wid}/activate")
    if "__error__" in act:
        print(f"[FAIL] activate {act['__error__']} {act.get('__body__')}")
        sys.exit(1)
    print("[ACTIVE] workflow activé")

    check = api("GET", f"/workflows/{wid}")
    node2 = next((n for n in check.get("nodes", []) if n.get("name") == NODE_NAME), None)
    ok = node2 is not None and node2["parameters"].get("text") == NEW_TEXT
    print(f"[{'OK' if ok else 'FAIL'}] vérification finale")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
