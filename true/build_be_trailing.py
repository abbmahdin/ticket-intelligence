#!/usr/bin/env python3
"""Crée (idempotent) et active le workflow n8n
« QuantLive - Breakeven & Trailing MT4 » (Priorité 3).

Flux : scheduleTrigger 30s -> GET /api/mt4/status -> Set (config depuis
$env, exprimée hors sandbox code) -> Code « Breakeven & Trailing » (calcule
les nouveaux SL) -> HTTP POST /api/mt4/accounts/{account}/modify par position
-> Telegram (notification uniquement quand une modif part).

La config se règle par variables d'env n8n (avec défauts) :
  BE_TRAILING_ENABLED        (defaut "true") — kill switch du workflow
  BE_TRAILING_BREAKEVEN_R    (defaut 1.0)    — breakeven à +1R
  BE_TRAILING_OFFSET_POINTS  (defaut 40)     — offset au-dessus de l'entrée
  BE_TRAILING_POINTS         (defaut 150)    — distance de trailing
  BE_TRAILING_MIN_MOVE       (defaut 20)     — delta mini pour modifier
"""
import json
import os
import sys
import urllib.request

KEY = open(os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")).read().strip()
BASE = "http://localhost:5678/api/v1"
H = {"X-N8N-API-KEY": KEY, "Content-Type": "application/json"}

WF_NAME = "QuantLive - Breakeven & Trailing MT4"
QL_URL = "{{ $env.QL_BASE_URL || 'http://localhost:8000' }}"
SECRET = "{{ $env.MINIAPP_SECRET }}"


def api(method, path, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "__body__": e.read().decode()[:400]}


def build_nodes():
    n = 0
    nodes = []

    def add(name, ntype, params, conns, tver=1, extra=None):
        nonlocal n
        node = {
            "parameters": params,
            "id": f"be_{n}",
            "name": name,
            "type": ntype,
            "typeVersion": tver,
            "position": conns,
        }
        if extra:
            node.update(extra)
        nodes.append(node)

    add(
        "Chaque 30s",
        "n8n-nodes-base.scheduleTrigger",
        {
            "rule": {
                "interval": [{"field": "seconds", "secondsInterval": 30}],
            },
        },
        [550, 300],
        1.2,
    )
    add(
        "Status MT4",
        "n8n-nodes-base.httpRequest",
        {
            "method": "GET",
            "url": f"={QL_URL}/api/mt4/status?k={SECRET}",
            "options": {"timeout": 6000},
        },
        [900, 300],
        4.2,
        extra={"maxTries": 3, "retryOnFail": True, "waitBetweenTries": 4000},
    )
    add(
        "Breakeven & Trailing",
        "n8n-nodes-base.code",
        {
            "jsCode": """// Lit le status MT4 (positions + bid/ask) et calcule les nouveaux SL.
// Miroir de app/services/position_manager.py (breakeven + trailing à cliquet)
// mais exécuté hors du cycle Python : aucune attente de 15 min.
// Config lue directement dans $env (N8N_BLOCK_ENV_ACCESS_IN_NODE=false,
// aligné sur le service principal et tous les workflows existants).
if (String($env.BE_TRAILING_ENABLED || 'true').toLowerCase() !== 'true') {
  return [];
}
const point = 0.01; // 1 point XAUUSD = 0.01 $
// [2026-08-23] Seuil abaisse de 1,0 R a 0,3 R.
    // Mesure : avec TP1_RR=0,4 et TP2_RR=0,6, le trade est INTEGRALEMENT
    // ferme avant d'atteindre +1 R. Le breakeven ne se posait donc JAMAIS --
    // ce workflow tournait toutes les 30 s sans jamais rien proteger.
    // 0,3 R laisse une fenetre reelle avant la prise partielle de 0,4 R.
    // A relever si la geometrie change (un TP1 a 1,2 R rendrait 1,0 R correct).
    // [2026-08-23] Remonte a 1,0 R : TP1_RR est passe de 0,4 a 1,2 et
    // TP2_RR de 0,6 a 1,8. Le trade a desormais le temps d'atteindre +1 R,
    // seuil auquel le breakeven protege sans couper les gagnants trop tot.
    // (Il avait ete abaisse a 0,3 tant que le trade sortait avant +1 R.)
    // [2026-08-24 — demande Redou « arme sur les deux bots »] Seuils PAR BOT.
// Un seuil unique est intenable : le principal vise TP1 a 1,2 R et TP2 a
// 1,8 R (~112 $), le micro scalpe. Mesure du 24/08 : le trailing reel du
// micro LIT est 0,10 x ATR M1 = 24 points, soit 0,24 $. Applique au
// principal, il le sortirait sur un recul de vingt-quatre centimes -- il
// n'atteindrait plus jamais son objectif.
//
// Principal : 1,0 R et 150 points, la geometrie pour laquelle il est calibre.
// Micro     : 0,3 R (= MICRO_BREAKEVEN_R) et 100 points.
//
// Pourquoi 100 et non 24 pour le micro : ce workflow est un FILET, pas le
// gestionnaire. La boucle micro traille deja a 24 points toutes les ~3 s.
// Un filet plus SERRE que le gestionnaire sortirait les positions avant lui
// et lui volerait ses gagnantes. Plus LACHE, il ne se declenche que quand la
// boucle ne repond plus -- exactement ce qu'on veut couvrir.
const beRPrincipal = Number($env.BE_TRAILING_BREAKEVEN_R) || 1.0;
const beRMicro = Number($env.BE_TRAILING_BREAKEVEN_R_MICRO) || 0.3;
const trailPrincipal = (Number($env.BE_TRAILING_POINTS) || 150) * 0.01;
const trailMicro = (Number($env.BE_TRAILING_POINTS_MICRO) || 100) * 0.01;
const beOffset = (Number($env.BE_TRAILING_OFFSET_POINTS) || 40) * point;

const minMove = (Number($env.BE_TRAILING_MIN_MOVE) || 20) * point;

const statuses = ($json.statuses || []);
const nowSec = Date.now() / 1000;
const out = [];
for (const s of statuses) {
  // Garde de fraîcheur : /api/mt4/status n'expose pas `stale`, on vérifie
  // l'âge du ts nous-mêmes (EA écrit à chaque tick, 120 s = terminal mort).
  const ts = Number(s.ts) || 0;
  if (!s.connected || s.no_data || !(ts > 0) || (nowSec - ts) > 120) continue;
  if (s.paused || s.kill_switch) continue;
  const account = s.account;
  const bid = Number(s.bid), ask = Number(s.ask);
  if (!(bid > 0) || !(ask > 0)) continue;
  for (const p of (s.positions || [])) {
    // Le bid/ask du status est celui du compte (TradeSymbol=XAUUSD hardcodé
    // dans l'EA) : ne gérer que les positions XAUUSD, sinon les niveaux
    // seraient calculés sur le mauvais prix de référence.
    if (p.symbol && p.symbol !== 'XAUUSD') continue;
        // [CLOISONNEMENT 2026-08-23] Ne gerer QUE les positions du bot
        // principal. Les deux micro deplacent deja leurs propres stops, a
        // chaque cycle (~3 s) et avec des seuils adaptes a leur geometrie :
        // breakeven +0,3 R et trailing relatif au risque, contre +1 R et
        // 150 points FIXES ici. Sur un scalp de 336 points, ce trailing est
        // quatre fois trop lache -- appliquer les seuils du bot principal a
        // du scalp degrade la protection au lieu de l'ameliorer.
        // Le champ `bot` vient de /api/mt4/status (mapping ids.txt).
        // Un ticket inconnu du mapping n'est reclame par personne : on le
        // laisse tranquille plutot que de deplacer un stop au hasard.
        // [2026-08-24] Le cloisonnement excluait les positions micro au
        // motif que « les deux micro deplacent deja leurs propres stops ».
        // VERIFIE le 24/08 : c'est FAUX. `app/micro/execution.py` n'envoie
        // que open, close, close_signal et close_all -- jamais modify. Le
        // breakeven et le trailing du micro sont un stop VIRTUEL evalue dans
        // la boucle Python, qui ferme au marche ; le SL reel chez le courtier
        // ne bouge JAMAIS. Boucle arretee (service tue, WSL redemarre, pont
        // MT4 perime) = position nue avec son SL d'origine.
        // Ce workflow devient le filet des trois bots : 30 s, cote serveur,
        // independant des boucles Python.
        // Un ticket inconnu du mapping ids.txt n'est reclame par personne :
        // on le laisse tranquille plutot que de deplacer un stop au hasard.
        if (!p.bot) continue;
        const estPrincipal = p.bot === 'principal';
        const beR = estPrincipal ? beRPrincipal : beRMicro;
        const trailDist = estPrincipal ? trailPrincipal : trailMicro;
    const tkt = Number(p.ticket);
    const entry = Number(p.open_price);
    const curSl = Number(p.sl);
    // Pas de gestion sans stop initial : cohérent avec position_manager
    // (le R se calcule sur le stop ; sans stop, rien à protéger).
    if (!(tkt > 0) || !(entry > 0) || !(curSl > 0)) continue;    const isBuy = p.type === 'BUY';
    const ref = isBuy ? bid : ask;
    // R mesuré sur le stop ACTUEL de la position (comme position_manager :
    // une fois le stop déplacé, le R initial est perdu — registre absent ici).
    // IMPORTANT : risk peut devenir <= 0 APRÈS le breakeven (BUY : curSl >= entry).
    // La garde ne doit donc protéger QUE la branche breakeven, jamais le
    // trailing — sinon le trailing serait one-shot (mort après le 1er move).
    const risk = isBuy ? entry - curSl : curSl - entry;

    let newSl = curSl;
    let rule = '';
    // [FIX 2026-08-24] `r` etait declare `const` DANS le bloc `if (risk > 0)`
    // et lu 26 lignes plus bas dans out.push : ReferenceError a CHAQUE
    // deplacement de stop. Le noeud levait donc une exception des qu'il avait
    // quelque chose a proteger -- la securisation des gains du bot principal
    // n'a jamais deplace un seul stop depuis le 23/08 20:09. Reproduit sous
    // node sur les quatre cas du banc : BE, trailing, micro, +0,3 R.
    let r = 0;
    // 1) Breakeven : dès +beR R, SL -> entrée + offset (coût de sortie).
    //    Uniquement tant que risk > 0 (stop encore du côté initial).
    if (risk > 0) {
      r = (isBuy ? ref - entry : entry - ref) / risk;
      if (r >= beR) {
        const be = isBuy ? entry + beOffset : entry - beOffset;
        const better = isBuy ? be > curSl : be < curSl;
        if (better) { newSl = be; rule = 'breakeven'; }
      }
    }
    // 2) Trailing à cliquet : après le breakeven (posé ce cycle OU déjà en
    //    place — curSl >= entrée pour BUY / <= entrée pour SELL), SL suit le
    //    prix de référence à trailDist derrière, jamais plus lâche. Indépendant
    //    de `risk` : tourne à chaque cycle une fois le BE acquis.
    if (rule === 'breakeven' || (isBuy ? curSl >= entry : curSl <= entry)) {
      // [FIX 2026-08-26 — Redou] risk <= 0 (BE posé à un cycle précédent) :
      // le R initial est perdu — pas de registre ici (même limite que
      // position_manager, qui mémorise initial_stop à la 1re observation).
      // Valeur affichée : beR, la borne atteinte — le stop n'a pu passer
      // au-dessus de l'entrée qu'en atteignant +beR, gain verrouillé par le
      // cliquet. Fini le « trailing à 0R » en notif.
      if (risk <= 0) { r = beR; }
      const trail = isBuy ? ref - trailDist : ref + trailDist;
      const better = isBuy ? trail > newSl : trail < newSl;
      if (better) { newSl = trail; rule = 'trailing'; }
    }
    // Pas de modification si le delta est sous le seuil anti-bruit.
    const delta = Math.abs(newSl - curSl);
    if (delta < minMove) continue;
    out.push({
      account,
      ticket: tkt,
      side: p.type,
      current_sl: curSl,
      new_sl: Number(newSl.toFixed(5)),
      rule,
      bot: p.bot,
      r: Number(r.toFixed(2)),
      price_ref: ref,
      symbol: p.symbol,
    });
  }
}
return out;""",
        },
        [1600, 300],
        2,
    )
    add(
        "Envoyer modify MT4",
        "n8n-nodes-base.httpRequest",
        {
            "method": "POST",
            "url": f"={QL_URL}/api/mt4/accounts/{{{{ $json.account }}}}/modify?k={SECRET}&ticket={{{{ $json.ticket }}}}&sl={{{{ $json.new_sl }}}}",
            "options": {"timeout": 6000},
            "sendBody": False,
        },
        [1950, 300],
        4.2,
        extra={"maxTries": 3, "retryOnFail": True, "waitBetweenTries": 4000},
    )
    add(
        "Notif Telegram BE/Trailing",
        "n8n-nodes-base.telegram",
        {
            "resource": "message",
            "operation": "sendMessage",
            "chatId": "={{ $env.TELEGRAM_DM_CHAT_ID || $env.TELEGRAM_CHAT_ID }}",
            "text": "=🔒 *Breakeven/Trailing MT4*\nCompte: {{ $('Breakeven & Trailing').item.json.account }}\nTicket: {{ $('Breakeven & Trailing').item.json.ticket }} ({{ $('Breakeven & Trailing').item.json.side }} {{ $('Breakeven & Trailing').item.json.symbol }})\nRègle: *{{ $('Breakeven & Trailing').item.json.rule }}* à {{ $('Breakeven & Trailing').item.json.r }}R\nSL: {{ $('Breakeven & Trailing').item.json.current_sl }} → *{{ $('Breakeven & Trailing').item.json.new_sl }}*\nRéf: {{ $('Breakeven & Trailing').item.json.price_ref }}",
            "additionalFields": {"parse_mode": "Markdown"},
        },
        [2300, 300],
        2.1,
        extra={
            "credentials": {
                "telegramApi": {"id": "a1cf4abee1304724", "name": "Telegram Bot"}
            },
            "webhookId": "be_tg_webhook",
        },
    )

    connections = {
        "Chaque 30s": {"main": [[{"node": "Status MT4", "type": "main", "index": 0}]]},
        "Status MT4": {"main": [[{"node": "Breakeven & Trailing", "type": "main", "index": 0}]]},
        "Breakeven & Trailing": {"main": [[{"node": "Envoyer modify MT4", "type": "main", "index": 0}]]},
        "Envoyer modify MT4": {"main": [[{"node": "Notif Telegram BE/Trailing", "type": "main", "index": 0}]]},
    }
    return nodes, connections


def main():
    nodes, connections = build_nodes()
    payload = {
        "name": WF_NAME,
        "nodes": nodes,
        "connections": connections,
        "settings": {"errorWorkflow": "9WrOGASQVKyErlmV", "executionOrder": "v1", "timezone": "Europe/Brussels"},
    }

    # Idempotence : workflow existant ?
    wfs = api("GET", "/workflows?limit=100").get("data", [])
    existing = [w for w in wfs if w.get("name") == WF_NAME]
    if existing:
        wid = existing[0]["id"]
        print(f"[EXIST] {WF_NAME} id={wid} active={existing[0].get('active')}")
        r = api("PUT", f"/workflows/{wid}", payload)
        if "__error__" in r:
            print(f"[FAIL] PUT {r['__error__']} {r.get('__body__')}")
            sys.exit(1)
        print("[PUT] workflow mis à jour")
    else:
        r = api("POST", "/workflows", payload)
        if "__error__" in r:
            print(f"[FAIL] POST {r['__error__']} {r.get('__body__')}")
            sys.exit(1)
        wid = r.get("id")
        print(f"[CREATE] {WF_NAME} id={wid}")

    act = api("POST", f"/workflows/{wid}/activate")
    if "__error__" in act:
        print(f"[FAIL] activate {act['__error__']} {act.get('__body__')}")
        sys.exit(1)
    print("[ACTIVE] workflow activé")

    # Vérification finale
    check = api("GET", f"/workflows/{wid}")
    print(f"  name={check.get('name')} active={check.get('active')} "
          f"nodes={len(check.get('nodes', []))}")
    if not check.get("active"):
        sys.exit(1)


if __name__ == "__main__":
    main()
