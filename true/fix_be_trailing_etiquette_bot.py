#!/usr/bin/env python3
"""Le filet BE/Trailing n8n ne reconnaissait plus le bot principal.

[2026-08-28] Le nœud Code « Breakeven & Trailing » teste :

    const estPrincipal = p.bot === 'principal';

Or `/api/mt4/status` n'a JAMAIS renvoyé « principal ». `_attribuer_bots`
(app/api/mt4_accounts.py, renommage du 25/08) émet exactement quatre valeurs :
`bot_principal`, `bot_micro`, `bot_lit`, `inconnu`. La comparaison est donc
fausse à chaque position depuis le 25/08 : le bot PRINCIPAL était protégé avec
les seuils du MICRO.

Conséquence, sur la position principale ouverte au moment du constat
(entrée 4610,28, SL 4556,93, soit 53,35 $ de risque) : au lieu de son filet
calibré (+1 R, trailing 150 points), il aurait reçu +0,5 R et un trailing de
100 points — 1,00 $ derrière le prix. Un bot dont le TP2 vise ~112 $ aurait
été sorti au premier recul d'un dollar. Le commentaire du nœud décrit
précisément ce danger... pour l'écarter, alors que le code le produisait.

Le nœud n'ayant encore jamais eu de position à +0,5 R depuis le renommage,
rien n'a été coupé : le défaut était armé, pas encore déclenché.

Correctif : comparer à `bot_principal`, en tolérant l'ancienne valeur
`principal` pour qu'une position ouverte avant le renommage reste attribuée.

Procédure identique à fix_be_trailing_notif.py (GET -> PUT -> activate ->
relecture) : un PUT seul ne change pas la version publiée.
"""
import json
import os
import sys
import urllib.request

KEY = open(
    os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")
).read().strip()
BASE = "http://localhost:5678/api/v1"
H = {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"}

WF_NAME = "QuantLive - Breakeven & Trailing MT4"
NODE_NAME = "Breakeven & Trailing"

ANCIEN = "const estPrincipal = p.bot === 'principal';"
NOUVEAU = (
    "// [2026-08-28] `/api/mt4/status` renvoie bot_principal/bot_micro/"
    "bot_lit\n"
    "        // (renommage du 25/08). La comparaison a 'principal' etait "
    "donc\n"
    "        // toujours fausse : le bot PRINCIPAL heritait des seuils du "
    "MICRO\n"
    "        // -- trailing a 1,00 $ pour un objectif a ~112 $. L'ancienne\n"
    "        // valeur reste toleree pour les positions d'avant le "
    "renommage.\n"
    "        const estPrincipal = "
    "(p.bot === 'bot_principal' || p.bot === 'principal');"
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
        print(f"[FAIL] noeud {NODE_NAME} introuvable")
        sys.exit(1)

    code = target["parameters"].get("jsCode", "")
    if NOUVEAU in code:
        print("[OK] etiquette deja corrigee, rien a faire")
        return
    if ANCIEN not in code:
        print("[FAIL] ligne attendue absente — le noeud a change, ne pas forcer")
        print(f"       cherche : {ANCIEN}")
        sys.exit(1)

    target["parameters"]["jsCode"] = code.replace(ANCIEN, NOUVEAU, 1)

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
    print("[PUT] workflow mis a jour")

    act = api("POST", f"/workflows/{wid}/activate")
    if "__error__" in act:
        print(f"[FAIL] activate {act['__error__']} {act.get('__body__')}")
        sys.exit(1)
    print("[ACTIVE] workflow active")

    check = api("GET", f"/workflows/{wid}")
    node2 = next(
        (n for n in check.get("nodes", []) if n.get("name") == NODE_NAME), None
    )
    ok = node2 is not None and NOUVEAU in node2["parameters"].get("jsCode", "")
    print(f"[{'OK' if ok else 'FAIL'}] verification finale (relecture live)")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
