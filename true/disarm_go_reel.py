"""Desarme le GO-GATE MT4 pour la phase demo.

Ecrit `go_reel: false` (avec note de phase) sur la copie Windows canonique
(lu par l'executeur) ET le miroir WSL versionne (reference de coherence
scripts/check_market_open.py, compare par hash) — symetrique de
safety.authorize_go_reel + _sync_gate_mirror.

Les chemins sont resolus via app.mt4_executor.paths (convention repo) ;
repli sur les valeurs verifiees si l'import n'est pas disponible.
"""
import json
import time
import hashlib
import sys
from pathlib import Path

QUANTLIVE_DIR = Path("/home/redou/QuantLive")
sys.path.insert(0, str(QUANTLIVE_DIR))

try:
    from app.mt4_executor.paths import go_gate_file, wsl_gate_file
    WIN_COPY = go_gate_file()
    WSL_COPY = wsl_gate_file()
    print(f"chemins resolus via app.mt4_executor.paths")
except ImportError:
    WIN_COPY = Path("/mnt/c/Users/redou/QuantLive_win/mt4_go_reel.json")
    WSL_COPY = QUANTLIVE_DIR / "mt4_go_reel.json"
    print("import app indisponible — repli chemins verifies")

payload = {
    "go_reel": False,
    "phase": "demo",
    "authorized_by": "Bots en phase DEMO depuis 2026-08-25 — GO-GATE desarme (go_reel=false), aucune validation humaine pour du reel",
    "ts": int(time.time()),
}

for p in (WIN_COPY, WSL_COPY):
    p.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"ecrit: {p}")

# Verification : hash identiques (check_market_open.py compare par hash)
h1 = hashlib.sha256(WIN_COPY.read_bytes()).hexdigest()
h2 = hashlib.sha256(WSL_COPY.read_bytes()).hexdigest()
print("hash coherent:", h1 == h2)

# Verification : le gate est bien desarme
print("\ncontenu final:")
print(WIN_COPY.read_text())
