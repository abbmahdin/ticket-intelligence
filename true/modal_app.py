"""Déploiement Modal des briques portables de QuantLive.

Ce que ce module déploie sur Modal :

1. ``micro_cycle`` — la VRAIE boucle du bot micro
   (``app.micro.loop.run_forever``), invoquée par cron chaque minute avec un
   budget de 55 s (≈ 15 cycles à 3 s), puis scale-to-zero. L'état persistant
   (``data/micro-trademax/*``, ``logs/micro.jsonl``) vit dans un Volume
   Modal monté sur ``/quantlive/data`` et ``/quantlive/logs``.

2. ``webapp`` — endpoint FastAPI de santé + statut micro lu depuis le
   Volume, sans dépendance Postgres.

Non portables (restent sur la machine Windows/WSL) : les terminaux MT4, le
heartbeat et l'exécution d'ordres (``app/mt4_executor``, ``/mnt/c``).

Limite assumée : sans un Postgres joignable (ex. le Postgres Railway, une
fois en ligne), ``_load_series`` échoue à chaque cycle et la boucle journalise
``cycle_erreur`` (fail-open, elle ne meurt jamais d'un cycle raté). Le
câblage ``DATABASE_URL`` du secret Modal vers un Postgres cloud le rend
fonctionnel sans redéploiement.
"""

from __future__ import annotations

import asyncio

from modal import App, Cron, Image, Secret, Volume, asgi_app

APP_NAME = "quantlive-micro"
VOLUME_NAME = "quantlive-micro-state"
SECRET_NAME = "quantlive-micro-trademax"

app = App(APP_NAME)
state = Volume.from_name(VOLUME_NAME, create_if_missing=True)
micro_secret = Secret.from_name(SECRET_NAME)

# Image allégée : torch/transformers ne sont pas importés au niveau module
# dans app/ (vérifié) — l'image se construit en 1-2 min au lieu de 10+.
image = (
    Image.debian_slim(python_version="3.12")
    .apt_install("libgomp1")
    .pip_install_from_requirements("requirements-modal.txt")
    .copy_local_dir("app", "/quantlive/app", ignore=["__pycache__", "*.pyc"])
)

WORKDIR = "/quantlive"
ENV = {"PYTHONPATH": "/quantlive"}
VOLUMES = {
    "/quantlive/data": state,
    "/quantlive/logs": state,
}

# Budget d'un cycle cron : 55 s sur 60 — le reste est la marge de scale-up.
CYCLE_BUDGET_S = 55.0


@app.function(
    image=image,
    secrets=[micro_secret],
    volumes=VOLUMES,
    schedule=Cron("* * * * *"),
    timeout=120,
    environment=ENV,
    workdir=WORKDIR,
)
def micro_cycle() -> dict:
    """Un cycle par minute : exécute la vraie boucle ~55 s, puis rend la main.

    ``run_forever`` est conçue pour ne jamais retourner ; on la bride avec
    ``asyncio.wait_for`` pour que l'invocation cron se termine proprement et
    que le conteneur scale-to-zero entre deux minutes.
    """
    from app.micro.loop import run_forever

    async def _bounded() -> str:
        task = asyncio.create_task(run_forever())
        try:
            await asyncio.wait_for(task, timeout=CYCLE_BUDGET_S)
        except asyncio.TimeoutError:
            task.cancel()
            return "budget écoulé"
        return "boucle terminée (anormal — signal reçu)"

    return {"resultat": asyncio.run(_bounded())}


# --- Web de santé -----------------------------------------------------------

from fastapi import FastAPI  # noqa: E402

web = FastAPI(title="QuantLive Micro — Modal")


@web.get("/health/live")
def live() -> dict:
    return {"status": "ok"}


@web.get("/health/ready")
def ready() -> dict:
    # Vert sans Postgres cloud : l'état du bot vient du Volume, pas de la DB.
    return {"status": "ok", "note": "sans dépendance Postgres"}


@web.get("/micro/status")
def micro_status() -> dict:
    """Statut micro : dernières lignes du ledger + fichiers d'état du Volume."""
    import json
    from pathlib import Path

    ledger = Path("/quantlive/logs/micro.jsonl")
    lignes: list[dict] = []
    if ledger.exists():
        with open(ledger, encoding="utf-8") as fh:
            for raw in list(fh)[-10:]:
                raw = raw.strip()
                if raw:
                    try:
                        lignes.append(json.loads(raw))
                    except json.JSONDecodeError:
                        lignes.append({"brut": raw[:200]})
    etats: dict[str, object] = {}
    for p in sorted(Path("/quantlive/data").glob("*/slots.json"))[-5:]:
        try:
            etats[str(p.relative_to("/quantlive/data"))] = json.loads(
                p.read_text(encoding="utf-8")
            )
        except Exception as exc:  # noqa: BLE001
            etats[str(p)] = {"erreur": str(exc)}
    return {"ledger_dernieres_lignes": lignes, "etats_slots": etats}


@app.function(
    image=image,
    secrets=[micro_secret],
    volumes=VOLUMES,
    environment=ENV,
    workdir=WORKDIR,
    allow_concurrent_inputs=20,
)
@asgi_app()
def webapp() -> FastAPI:
    return web