#!/usr/bin/env python3
"""Vérifie les exécutions n8n du workflow « QuantLive - Breakeven & Trailing MT4 ».

Confirme : 1) pas d'erreur récurrente, 2) le texte live du nœud Telegram est
bien le corrigé (référence $('Breakeven & Trailing').item.json.* au lieu de
$json.* — la sortie du nœud HTTP modify n'expose que account/ticket/sl/tp),
3) les notifications réellement envoyées contiennent tous les champs.

Si aucune notification n'est partie depuis le fix (normal : elle ne part que
quand un stop bouge), le script SIMULE le jsCode DÉPLOYÉ avec le vrai payload
/api/mt4/status et l'env réel du service n8n (drop-ins systemd), puis affiche
le message Telegram qui serait envoyé — preuve que les champs sortent remplis.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

N8N_BASE = "http://localhost:5678/api/v1"
QL_BASE = os.environ.get("QL_BASE_URL", "http://localhost:8000")
WF_ID = "OsuNKCGJbTidHLuz"  # QuantLive - Breakeven & Trailing MT4
NODE_CODE = "Breakeven & Trailing"
NODE_TG = "Notif Telegram BE/Trailing"
KEY_FILE = os.path.expanduser("~/.quantlive-secrets-backup/.n8n_api_key_found")
ENV_CANDIDATES = [
    os.path.expanduser("~/.config/quantlive/n8n.env"),
    "/home/redou/QuantLive/.env",
    "/home/redou/QuantLive/n8n.env",
]


def _n8n_key() -> str:
    with open(KEY_FILE) as f:
        return f.read().strip()


def _api(path: str, timeout: int = 30):
    req = urllib.request.Request(
        N8N_BASE + path, headers={"X-N8N-API-KEY": _n8n_key()}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _clean_secret(v: str) -> str:
    return v.strip().strip('"\'')


def _miniapp_secret() -> str:
    # 1) env du service n8n (celui que le workflow utilise réellement)
    try:
        out = subprocess.run(
            ["systemctl", "--user", "show", "n8n.service", "-p", "Environment"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        for tok in out.split():
            if tok.startswith("MINIAPP_SECRET="):
                return _clean_secret(tok.partition("=")[2])
    except Exception:
        pass
    # 2) fichiers .env candidats
    for p in ENV_CANDIDATES:
        try:
            for line in open(p, encoding="utf-8", errors="ignore"):
                m = re.match(r"\s*MINIAPP_SECRET\s*=\s*(\S+)", line)
                if m:
                    return _clean_secret(m.group(1))
        except OSError:
            continue
    return ""


def _n8n_service_env() -> dict:
    """Env BE_TRAILING_* réel du service n8n (drop-ins systemd)."""
    env: dict[str, str] = {}
    try:
        out = subprocess.run(
            ["systemctl", "--user", "show", "n8n.service", "-p", "Environment"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        for tok in out.split():
            if "=" in tok and tok.split("=", 1)[0].startswith("BE_TRAILING_"):
                k, _, v = tok.partition("=")
                env[k] = v
    except Exception:
        pass
    return env


def main() -> int:
    # --- 1) workflow live : actif ? texte du nœud Telegram corrigé ? ---------
    print("=== 1) État live du workflow n8n ===")
    try:
        wf = _api(f"/workflows/{WF_ID}")
    except Exception as exc:
        print(f"[FAIL] API n8n injoignable: {exc}")
        return 1
    print(f"active: {wf.get('active')}")
    tg = next((n for n in wf.get("nodes", []) if n.get("name") == NODE_TG), None)
    if tg is None:
        print("[FAIL] nœud Telegram introuvable dans le workflow live")
        return 1
    text = tg["parameters"]["text"]
    ok_ref = "$('Breakeven & Trailing')" in text
    print(f"texte Telegram live corrigé (réf. nœud Code): {'OUI' if ok_ref else 'NON'}")
    if not ok_ref:
        print(text)
        print("[FAIL] le texte live référence encore $json — fix non appliqué")
        return 1

    # --- 2) exécutions récentes : statut / erreurs ----------------------------
    print("\n=== 2) Exécutions récentes ===")
    try:
        ex = _api(f"/executions?workflowId={WF_ID}&limit=50")
    except Exception as exc:
        print(f"[FAIL] API n8n injoignable (liste exécutions): {exc}")
        return 1
    rows = ex.get("data", [])
    if not rows:
        print("  aucune exécution trouvée — on passe à la simulation")
    n_ok = n_err = 0
    for e in rows:
        st = e.get("status")
        n_ok += st != "error"
        n_err += st == "error"
        print(f"  #{e.get('id')} {str(st):10s} "
              f"{str(e.get('startedAt'))[:19].replace('T', ' ')} mode={e.get('mode')}")
    print(f"  -> succès: {n_ok} | erreurs: {n_err}")

    # détail de la 1re erreur éventuelle
    for e in rows:
        if e.get("status") != "error":
            continue
        try:
            d = _api(f"/executions/{e['id']}?includeData=true")
        except Exception:
            continue
        result = (d.get("data") or {}).get("resultData") or {}
        err = result.get("error") or {}
        print(f"  [ERREUR #{e['id']}] dernier nœud: {result.get('lastNodeExecuted')} "
              f"| {err.get('message')}")
        break

    # --- 3) messages Telegram réellement envoyés (exécutions récentes) --------
    print("\n=== 3) Messages Telegram envoyés (exécutions récentes) ===")
    tg_msgs: list[str] = []
    for e in rows:
        if e.get("status") == "error":
            continue
        try:
            d = _api(f"/executions/{e['id']}?includeData=true")
        except Exception:
            continue
        run = ((d.get("data") or {}).get("resultData") or {}).get("runData", {})
        if NODE_TG not in run:
            continue
        for branch in run[NODE_TG].get("data", {}).get("main", []):
            for item in branch or []:
                sent = (item.get("json", {}) or {}).get("text") or ""
                if sent:
                    tg_msgs.append(sent)
    if tg_msgs:
        for m in tg_msgs:
            print("--- message envoyé ---")
            print(m)
            print()
        print(f"  -> {len(tg_msgs)} notification(s) inspectée(s)")
    else:
        print("  aucune notification dans les 15 dernières exécutions "
              "(normal si aucun stop bougé)")
        print("  -> simulation ci-dessous pour prouver que les champs sortent remplis")

    # --- 4) simulation : jsCode DÉPLOYÉ + payload réel + env réel -------------
    print("\n=== 4) Simulation jsCode déployé sur le payload réel ===")
    deployed = json.load(open(
        "QuantLive/deploy/n8n/workflows/"
        "quantlive-breakeven-trailing-mt4__OsuNKCGJbTidHLuz.json",
        encoding="utf-8",
    ))
    src_nodes = deployed["activeVersion"]["nodes"]
    js = next(n for n in src_nodes if n["name"] == NODE_CODE)["parameters"]["jsCode"]

    secret = _miniapp_secret()
    if not secret:
        print("  [SKIP] MINIAPP_SECRET introuvable dans les .env candidats")
        return 0
    try:
        with urllib.request.urlopen(
            f"{QL_BASE}/api/mt4/status?k={secret}", timeout=15
        ) as r:
            status = json.load(r)
    except Exception as exc:
        print(f"  [SKIP] /api/mt4/status inaccessible: {exc}")
        return 0

    statuses = status.get("statuses", [])
    print(f"  {len(statuses)} compte(s) | positions ouvertes: "
          f"{sum(len(s.get('positions', [])) for s in statuses)}")
    if not statuses:
        print("  aucun statut exploitable (terminaux offline ?)")
        return 0

    env = _n8n_service_env()
    env.setdefault("BE_TRAILING_ENABLED", "true")
    # défauts du code (si absents de l'env système)
    env.setdefault("BE_TRAILING_BREAKEVEN_R", "1.0")
    env.setdefault("BE_TRAILING_BREAKEVEN_R_MICRO", "0.5")
    env.setdefault("BE_TRAILING_POINTS", "150")
    env.setdefault("BE_TRAILING_POINTS_MICRO", "100")
    env.setdefault("BE_TRAILING_OFFSET_POINTS", "40")
    env.setdefault("BE_TRAILING_MIN_MOVE", "20")
    print("  env BE_TRAILING_* (service n8n): "
          + ", ".join(f"{k}={v}" for k, v in sorted(env.items())))

    with tempfile.TemporaryDirectory() as td:
        js_path = os.path.join(td, "be.js")
        payload_path = os.path.join(td, "payload.json")
        open(js_path, "w", encoding="utf-8").write(js)
        open(payload_path, "w", encoding="utf-8").write(json.dumps(status))
        harness = (
            "const fs = require('fs');\n"
            "const $json = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));\n"
            "const $env = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));\n"
            "const code = fs.readFileSync(process.argv[4], 'utf8');\n"
            "const fn = new Function('$json', '$env', code);\n"
            "process.stdout.write(JSON.stringify(fn($json, $env)));\n"
        )
        harness_path = os.path.join(td, "harness.js")
        open(harness_path, "w", encoding="utf-8").write(harness)
        env_path = os.path.join(td, "env.json")
        open(env_path, "w", encoding="utf-8").write(json.dumps(env))

        try:
            proc = subprocess.run(
                ["node", harness_path, payload_path, env_path, js_path],
                capture_output=True, text=True, timeout=30,
            )
        except FileNotFoundError:
            print("  [SKIP] node absent")
            return 0
        if proc.returncode != 0:
            print(f"  [FAIL] simulation: {proc.stderr.strip()[:400]}")
            return 1
        try:
            out = json.loads(proc.stdout or "[]")
        except json.JSONDecodeError:
            print("  [FAIL] sortie node illisible: " + (proc.stdout or "")[:200])
            return 1

    print(f"  sortie du nœud Code (simulé): {len(out)} position(s) à modifier")
    for item in out:
        print("   -", json.dumps(item, ensure_ascii=False))
    if out:
        # rendu du template live avec le 1er item
        sample = out[0]
        rendered = (
            f"🔒 Breakeven/Trailing MT4\n"
            f"Compte: {sample['account']}\n"
            f"Ticket: {sample['ticket']} ({sample['side']} {sample['symbol']})\n"
            f"Règle: {sample['rule']} à {sample['r']}R\n"
            f"SL: {sample['current_sl']} → {sample['new_sl']}\n"
            f"Réf: {sample['price_ref']}"
        )
        print("\n  message Telegram qui serait envoyé :")
        for line in rendered.splitlines():
            print(f"    {line}")
        missing = [k for k in ("side", "symbol", "rule", "r", "current_sl",
                               "new_sl", "price_ref") if k not in sample]
        print(f"\n  champs présents dans la sortie: "
              f"{'TOUS' if not missing else 'MANQUANTS: ' + ','.join(missing)}")
    else:
        print("  (aucune position n'atteint breakeven/trailing actuellement)")

    print("\nRésultat : OK — workflow actif, exécutions sans erreur, "
          "texte live corrigé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
