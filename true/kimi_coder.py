#!/usr/bin/env python3
"""Agent de code CLI utilisant Kimi K3 via OpenRouter.

Usage:
  kimi "instruction de codage" [--path /chemin/projet]
  kimi --file tache.md          # lit la tache depuis un fichier

Le modele (moonshotai/kimi-k3) tourne sur OpenRouter (cloud). L'agent execute
sur ton PC: lit/ecrire fichiers, lance des commandes shell, boucle jusqu'a
resolution. CLE: OPENROUTER_API_KEY (export ou dans ~/.env).

Outils exposes au modele:
  read_file(path, offset, limit)
  write_file(path, content)
  patch_file(path, old, new)
  search(pattern, path, glob)
  bash(command)
  list_dir(path)
"""

import os
import sys
import json
import asyncio
import httpx
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path.home() / ".env")
except Exception:
    pass

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL = os.environ.get("KIMI_MODEL", "moonshotai/kimi-k3")
BASE = "https://openrouter.ai/api/v1/chat/completions"
SITE_URL = "https://github.com/redou/quantlive"
APP_NAME = "KimiCoder"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lit un fichier (avec numeros de ligne). offset/limit optionnels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "offset": {"type": "integer", "default": 1},
                    "limit": {"type": "integer", "default": 200},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Remplace tout le contenu d'un fichier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "patch_file",
            "description": "Remplace une occurrence de texte par une autre dans un fichier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old": {"type": "string"},
                    "new": {"type": "string"},
                },
                "required": ["path", "old", "new"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Recherche un motif regex dans les fichiers (ripgrep).",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string", "default": "."},
                    "glob": {"type": "string", "default": "*"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute une commande shell (foreground). Retourne stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer", "default": 120},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "Liste le contenu d'un repertoire.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "default": "."}},
            },
        },
    },
]


def tool_read_file(path, offset=1, limit=200):
    p = Path(path)
    if not p.exists():
        return f"FICHIER INTROUVABLE: {path}"
    lines = p.read_text(errors="replace").splitlines()
    seg = lines[offset - 1 : offset - 1 + limit]
    return "\n".join(f"{i+offset}|{l}" for i, l in enumerate(seg))


def tool_write_file(path, content):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content, encoding="utf-8")
    return f"ECRIT: {path} ({len(content)} chars)"


def tool_patch_file(path, old, new):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    if old not in s:
        return f"PATCH ECHEC: motif introuvable dans {path}"
    s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    return f"PATCH OK: {path}"


def tool_search(pattern, path=".", glob="*"):
    import subprocess
    if subprocess.run(["which", "rg"], capture_output=True).returncode == 0:
        r = subprocess.run(
            ["rg", "--line-number", "--max-count", "5", "--glob", glob, pattern, path],
            capture_output=True, text=True,
        )
        return r.stdout or r.stderr or "aucun resultat"
    # fallback grep
    r = subprocess.run(
        f"grep -rnE --include='{glob}' -m5 '{pattern}' {path}",
        shell=True, capture_output=True, text=True,
    )
    return r.stdout or r.stderr or "aucun resultat"


def tool_bash(command, timeout=120):
    import subprocess
    r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr)[:4000] or "(vide)"


def tool_list_dir(path="."):
    import subprocess
    r = subprocess.run(["ls", "-la", path], capture_output=True, text=True)
    return r.stdout or r.stderr


TOOL_FUNCS = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "patch_file": tool_patch_file,
    "search": tool_search,
    "bash": tool_bash,
    "list_dir": tool_list_dir,
}


SYSTEM = (
    "Tu es un agent de code experimente. Tu travailles sur le projet a {cwd}. "
    "Utilise les outils pour lire/modifier/executer. Boucle jusqu'a resolution complete. "
    "Sois concis. Apres chaque action, dis ce que tu observes et la suite. "
    "Quand c'est fini, resume les changements en francais."
)


async def run(task: str, cwd: str):
    if not API_KEY:
        print("❌ OPENROUTER_API_KEY manquant. Exporte la variable ou mets-la dans ~/.env")
        return
    os.chdir(cwd)
    messages = [
        {"role": "system", "content": SYSTEM.format(cwd=cwd)},
        {"role": "user", "content": task},
    ]
    print(f"🤖 Kimi K3 ({MODEL}) — tache: {task[:80]}...")
    async with httpx.AsyncClient(timeout=300) as client:
        for step in range(25):
            r = await client.post(
                BASE,
                headers={"Authorization": f"Bearer {API_KEY}", "HTTP-Referer": SITE_URL, "X-Title": APP_NAME},
                json={"model": MODEL, "messages": messages, "tools": TOOLS, "tool_choice": "auto", "temperature": 0.2, "max_tokens": 2000},
            )
            if r.status_code != 200:
                print("ERREUR API:", r.status_code, r.text[:300])
                return
            data = r.json()
            msg = data["choices"][0]["message"]
            if not msg.get("tool_calls"):
                print("\n✅ KIMI:\n", msg["content"])
                return
            messages.append(msg)
            for tc in msg["tool_calls"]:
                fn = tc["function"]
                name = fn["name"]
                args = json.loads(fn.get("arguments", "{}"))
                print(f"  🔧 {name}({ {k: (str(v)[:40]) for k, v in args.items()} })")
                res = TOOL_FUNCS[name](**args)
                messages.append({"role": "tool", "content": str(res), "tool_call_id": tc["id"]})


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: kimi \"instruction\" [--path /projet] | kimi --file tache.md")
        return
    cwd = os.getcwd()
    task = ""
    if args[0] == "--file":
        task = Path(args[1]).read_text(encoding="utf-8")
    else:
        i = 0
        while i < len(args):
            if args[i] == "--path":
                cwd = args[i + 1]
                i += 2
            else:
                task += args[i] + " "
                i += 1
        task = task.strip()
    asyncio.run(run(task, cwd))


if __name__ == "__main__":
    main()
