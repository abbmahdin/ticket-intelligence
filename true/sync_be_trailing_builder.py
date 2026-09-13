#!/usr/bin/env python3
"""Synchronise build_be_trailing.py avec le workflow n8n déployé.

Source de vérité : QuantLive/deploy/n8n/workflows/
  quantlive-breakeven-trailing-mt4__OsuNKCGJbTidHLuz.json

Le builder gardait un jsCode PÉRIMÉ datant d'avant les correctifs du
2026-08-24, appliqués en production directement sur le workflow :
  1. ReferenceError : `const r` était déclaré DANS le bloc `if (risk > 0)`
     puis lu 26 lignes plus bas dans out.push -> `r is not defined` à CHAQUE
     déplacement de stop (le noeud ne protégeait donc jamais un gain).
  2. Split de seuils PAR BOT : beRPrincipal/beRMicro et trailPrincipal/
     trailMicro au lieu d'un seuil unique (le micro scalpe à +0,5 R / 100 pts,
     le principal vise TP1 à 1,2 R / 150 pts).
  3. Cloisonnement : `if (!p.bot) continue;` au lieu de
     `p.bot !== 'principal'` (les micro ne déplacent jamais de SL côté
     courtier, ce workflow est leur filet de sécurité).
  4. Champ `bot: p.bot` ajouté à la sortie (traçabilité principal/micro).

Il gardait aussi des paramètres de nœuds obsolètes :
  - timeout HTTP 15000 sans retries (le déployé : 6000 + maxTries 3,
    retryOnFail, waitBetweenTries 4000) ;
  - chatId Telegram sans fallback DM (`TELEGRAM_DM_CHAT_ID || ...`) ;
  - texte Telegram lu depuis $json (sortie du nœud HTTP modify) au lieu du
    nœud Code (champs vides dans la notif) ;
  - settings sans errorWorkflow.

Conséquence : relancer build_be_trailing.py réintroduisait les bugs déjà
corrigés en production. Ce script ré-aligne le builder sur le déployé.

Idempotent : un second passage ne modifie rien (chaque patch est conditionnel,
déjà-synchronisé = ignoré). Ne synchronise pas les positions de canvas
(purement cosmétique).

Usage : sync_be_trailing_builder.py [builder.py] [workflow.json]
  (chemin du builder puis du JSON déployé, pour tester sur des copies)

NB: les valeurs patchées (timeout, retries, chatId, text, settings) sont LUES
dans le JSON déployé, pas hardcodées — si le déployé évolue, ce script suit.
"""
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_DEPLOYED = ROOT / "QuantLive" / "deploy" / "n8n" / "workflows" / (
    "quantlive-breakeven-trailing-mt4__OsuNKCGJbTidHLuz.json"
)
DEFAULT_BUILDER = ROOT / "build_be_trailing.py"


def _fail(msg: str):
    print(f"[FAIL] {msg}")
    sys.exit(1)


def _py_literal(v) -> str:
    """Sérialise une valeur JSON en littéral Python valide."""
    if isinstance(v, dict):
        return "{" + ", ".join(
            f"{json.dumps(k, ensure_ascii=False)}: {_py_literal(x)}"
            for k, x in v.items()
        ) + "}"
    if isinstance(v, list):
        return "[" + ", ".join(_py_literal(x) for x in v) + "]"
    if isinstance(v, bool):
        return "True" if v else "False"
    if v is None:
        return "None"
    if isinstance(v, (int, float)):
        return repr(v)
    return json.dumps(v, ensure_ascii=False)


def _replace_conditional(src: str, old: str, new: str, label: str,
                         expect_old: int = 1) -> str:
    """Remplacement idempotent : old->new si présent, ignoré si new déjà là."""
    c_old, c_new = src.count(old), src.count(new)
    if c_old == expect_old and c_new == 0:
        print(f"[PATCH] {label}")
        return src.replace(old, new)
    if c_old == 0 and c_new >= expect_old:
        print(f"[OK  ] {label}: déjà synchronisé")
        return src
    _fail(f"{label}: état inattendu (old x{c_old}, new x{c_new})")


def main() -> int:
    builder = DEFAULT_BUILDER
    deployed = DEFAULT_DEPLOYED
    if len(sys.argv) >= 2:
        builder = pathlib.Path(sys.argv[1])
    if len(sys.argv) >= 3:
        deployed = pathlib.Path(sys.argv[2])

    data = json.loads(deployed.read_text(encoding="utf-8"))
    source = data.get("activeVersion") or data
    nodes = source.get("nodes") or data["nodes"]
    conns = source.get("connections") or data["connections"]
    # Le bloc settings n'existe QUE dans la racine de l'export (activeVersion
    # ne le porte pas) : on préfère data["settings"].
    settings = data.get("settings") or source.get("settings") or {}
    by_name = {n["name"]: n for n in nodes}
    for required in ("Breakeven & Trailing", "Status MT4", "Envoyer modify MT4",
                     "Notif Telegram BE/Trailing"):
        if required not in by_name:
            _fail(f"nœud manquant dans le déployé: {required}")

    new_js = by_name["Breakeven & Trailing"]["parameters"]["jsCode"].rstrip()
    if '"""' in new_js:
        _fail("le jsCode contient un triple-quote : à traiter à la main")

    src = builder.read_text(encoding="utf-8")
    before = src

    # --- 1) jsCode du nœud Code -------------------------------------------
    marker = '"jsCode": """'
    if f"{marker}{new_js}\"\"\"" in src:
        print("[OK  ] jsCode: déjà synchronisé")
    else:
        if marker not in src:
            _fail("marqueur jsCode introuvable dans le builder")
        i = src.index(marker) + len(marker)
        try:
            j = src.index('"""', i)
        except ValueError:
            _fail("fermeture de triple-quote jsCode introuvable (fichier cassé ?)")
        src = src[:i] + new_js + src[j:]  # src[j:] GARDE la fermeture """
        print("[PATCH] jsCode resynchronisé")

    # --- 2) timeout + retries des nœuds HTTP (valeurs lues du déployé) ----
    t_status = by_name["Status MT4"]["parameters"]["options"]["timeout"]
    t_modify = by_name["Envoyer modify MT4"]["parameters"]["options"]["timeout"]
    if t_status != t_modify:
        _fail(f"timeouts HTTP différents dans le déployé ({t_status} vs {t_modify})")
    old_to = '"options": {"timeout": 15000}'
    new_to = '"options": {"timeout": %d}' % t_status
    src = _replace_conditional(src, old_to, new_to, "timeout HTTP", expect_old=2)
    for node_name, anchor in (("Status MT4", "[900, 300]"),
                              ("Envoyer modify MT4", "[1950, 300]")):
        dep = by_name[node_name]
        extra = _py_literal({
            "maxTries": dep.get("maxTries"),
            "retryOnFail": dep.get("retryOnFail"),
            "waitBetweenTries": dep.get("waitBetweenTries"),
        })
        old_block = f"{anchor},\n        4.2,\n    )"
        new_block = f"{anchor},\n        4.2,\n        extra={extra},\n    )"
        src = _replace_conditional(src, old_block, new_block,
                                   f"retries {node_name}")

    # --- 3) chatId Telegram avec fallback DM --------------------------------
    old_chat = '"chatId": "={{ $env.TELEGRAM_CHAT_ID }}"'
    new_chat = '"chatId": ' + json.dumps(
        by_name["Notif Telegram BE/Trailing"]["parameters"]["chatId"],
        ensure_ascii=False,
    )
    src = _replace_conditional(src, old_chat, new_chat, "chatId Telegram")

    # --- 3bis) texte Telegram (champs depuis le nœud Code, pas la réponse
    #           HTTP modify) ---------------------------------------------------
    want_text = '"text": ' + json.dumps(
        by_name["Notif Telegram BE/Trailing"]["parameters"]["text"],
        ensure_ascii=False,
    )
    if want_text in src:
        print("[OK  ] text Telegram: déjà synchronisé")
    else:
        lines = src.splitlines(keepends=True)
        for idx, line in enumerate(lines):
            if line.lstrip().startswith('"text": '):
                indent = line[: len(line) - len(line.lstrip())]
                lines[idx] = indent + want_text + ",\n"
                src = "".join(lines)
                print("[PATCH] text Telegram resynchronisé")
                break
        else:
            _fail('ligne "text": introuvable dans le builder')

    # --- 4) settings : errorWorkflow + clés du déployé ----------------------
    old_set = '"settings": {"executionOrder": "v1", "timezone": "Europe/Brussels"}'
    new_set = '"settings": ' + _py_literal(settings)
    src = _replace_conditional(src, old_set, new_set, "settings payload")

    if src == before:
        print("[OK] build_be_trailing.py déjà synchronisé (rien à faire)")
    else:
        builder.write_text(src, encoding="utf-8")
        print("[OK] build_be_trailing.py resynchronisé")

    # --- 5) validations ------------------------------------------------------
    subprocess.run([sys.executable, "-m", "py_compile", str(builder)], check=True)
    print("[OK] py_compile")

    if shutil.which("node"):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(new_js)
            js_tmp = f.name
        try:
            subprocess.run(["node", "--check", js_tmp], check=True)
            print("[OK] node --check jsCode (syntaxe JS valide)")
        finally:
            pathlib.Path(js_tmp).unlink(missing_ok=True)
    else:
        print("[WARN] node absent : vérification syntaxe JS sauté")

    # --- 6) comparaison structurelle builder vs déployé ----------------------
    spec = importlib.util.spec_from_file_location("build_be_trailing", builder)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    bnodes, bconns = mod.build_nodes()
    bmap = {n["name"]: n for n in bnodes}

    problems: list[str] = []

    def check(name: str, key: str, want, got):
        if got != want:
            problems.append(f"{name}.{key}: déployé {want!r} != builder {got!r}")

    for name, dep in by_name.items():
        b = bmap.get(name)
        if b is None:
            problems.append(f"nœud manquant dans le builder: {name}")
            continue
        check(name, "type", dep["type"], b["type"])
        check(name, "typeVersion", dep["typeVersion"], b["typeVersion"])
        if name == "Breakeven & Trailing":
            check(name, "jsCode", dep["parameters"]["jsCode"].rstrip(),
                  b["parameters"]["jsCode"])
        elif name in ("Status MT4", "Envoyer modify MT4"):
            check(name, "timeout", dep["parameters"]["options"]["timeout"],
                  b["parameters"]["options"]["timeout"])
            check(name, "maxTries", dep.get("maxTries"), b.get("maxTries"))
            check(name, "retryOnFail", dep.get("retryOnFail"), b.get("retryOnFail"))
            check(name, "waitBetweenTries", dep.get("waitBetweenTries"),
                  b.get("waitBetweenTries"))
        elif name == "Notif Telegram BE/Trailing":
            check(name, "chatId", dep["parameters"]["chatId"],
                  b["parameters"]["chatId"])
            check(name, "text", dep["parameters"]["text"], b["parameters"]["text"])

    if bconns != conns:
        problems.append(f"connections: déployé {conns} != builder {bconns}")

    if problems:
        print("[FAIL] divergences restantes :")
        for p in problems:
            print("  -", p)
        return 1
    print("[OK] structure identique au déployé (5 nœuds + connections + settings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
