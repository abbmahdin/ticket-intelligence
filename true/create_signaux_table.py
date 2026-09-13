#!/usr/bin/env python3
"""Crée la table `signaux` dans la base `quantlive` (cible de la credential
n8n « QuantLive Postgres » : 127.0.0.1:5435/quantlive).

Le noeud Postgres « Archivage Postgres » du workflow « Archivage Signaux »
insère dans `signaux` les colonnes produites par « Formatage Signal » :
    date_signal, symbole, direction, prix, source, payload.

Types retenus selon la sortie du noeud Code :
    date_signal -> TIMESTAMPTZ   (nouvel Date().toISOString())
    symbole     -> VARCHAR
    direction   -> VARCHAR
    prix        -> NUMERIC NULL  (peut valoir null)
    source      -> VARCHAR
    payload     -> TEXT          (JSON.stringify(body))

Idempotent : CREATE TABLE IF NOT EXISTS — se relance sans effet de bord.
"""
from __future__ import annotations

import os
import sys

DDL = """
CREATE TABLE IF NOT EXISTS signaux (
    id           BIGSERIAL PRIMARY KEY,
    date_signal  TIMESTAMPTZ,
    symbole      VARCHAR(64),
    direction    VARCHAR(16),
    prix         NUMERIC,
    source       VARCHAR(64),
    payload      TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def main() -> int:
    if "N8N_PGPW" not in os.environ:
        print("N8N_PGPW manquant", file=sys.stderr)
        return 2
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ.get("N8N_PG_HOST", "127.0.0.1"),
        port=int(os.environ.get("N8N_PG_PORT", "5435")),
        user=os.environ.get("N8N_PG_USER", "quantlive"),
        password=os.environ["N8N_PGPW"],
        dbname=os.environ.get("N8N_PG_DB", "quantlive"),
    )
    conn.autocommit = False
    try:
        cur = conn.cursor()
        cur.execute(DDL)
        conn.commit()
        print("OK : table `signaux` creee (ou deja presente) dans quantlive.")
        return 0
    except Exception as e:  # noqa: BLE001
        conn.rollback()
        print(f"ECHEC : {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())