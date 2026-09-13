#!/usr/bin/env python3
"""Watchdog pour surveiller les modifications de Claude Code dans QuantLive.

Surveille les dossiers clés du projet QuantLive en polling, logue les fichiers
modifiés/créés/supprimés en temps réel, et génère un résumé final quand le
processus Claude Code (codex) ou sa session tmux n'est plus actif.

Usage:
    cd /home/redou
    python3 watchdog_claude_quantlive.py
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from time import sleep

import psutil

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_DIR = Path("/home/redou/QuantLive")
OUTPUT_DIR = Path("/home/redou")
LOG_FILE = OUTPUT_DIR / "watchdog_claude_quantlive.log"
SUMMARY_FILE = OUTPUT_DIR / "watchdog_claude_quantlive_summary.json"
PID_FILE = OUTPUT_DIR / "watchdog_claude_quantlive.pid"

# Dossiers surveillés (relatifs à PROJECT_DIR)
WATCHED_SUBDIRS = ["app", "tests", "scripts", "docs", "alembic", "artifacts/backtests"]

# Motifs à exclure du scan
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".codegraph", "node_modules"}
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".log", ".tmp", ".swp", ".swo", "~")

# Intervalle de polling (secondes)
POLL_INTERVAL = 3.0

# Intervalle entre deux snapshots git (secondes)
GIT_SNAPSHOT_INTERVAL = 30.0

# Nombre max d'événements gardés en mémoire pour le résumé final
MAX_CHANGES_IN_MEMORY = 500

# Temps minimum avant de déclarer Claude Code arrêté (secondes)
MIN_CONFIRMATION_SECONDS = 10

# Nombre de cycles entre deux heartbeats
HEARTBEAT_CYCLES = 10

# Noms de processus / commandes associés à Claude Code
CODEX_KEYWORDS = ("codex", "codegraph", "claude")
CODEX_TMUX_SESSION = "codex-permanent"


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    logger = logging.getLogger("watchdog_claude")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.FileHandler(LOG_FILE, mode="a")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    logger.addHandler(handler)
    logger.addHandler(stream)
    return logger


logger = setup_logging()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_excluded(path: Path) -> bool:
    """Retourne True si le chemin doit être ignoré."""
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
        if any(part.endswith(suffix) for suffix in EXCLUDE_SUFFIXES):
            return True
    return False


def get_snapshot() -> dict[str, dict]:
    """Capture l'état actuel des fichiers surveillés."""
    snap: dict[str, dict] = {}
    for sub in WATCHED_SUBDIRS:
        base = PROJECT_DIR / sub
        if not base.exists():
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for name in files:
                path = Path(root) / name
                if is_excluded(path):
                    continue
                try:
                    st = path.stat()
                    snap[str(path)] = {
                        "mtime": st.st_mtime,
                        "size": st.st_size,
                    }
                except OSError:
                    pass
    return snap


def find_codex_processes() -> list[psutil.Process]:
    """Retourne la liste des processus liés à Claude Code / Codex."""
    found: list[psutil.Process] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = " ".join(proc.info["cmdline"] or [""])
            name = proc.info["name"] or ""
            if any(kw in name.lower() or kw in cmd.lower() for kw in CODEX_KEYWORDS):
                found.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return found


def codex_is_alive() -> bool:
    """True si Claude Code tourne encore (process codex/codegraph)."""
    return bool(find_codex_processes())


def git_status() -> dict:
    """Capture git status, diff et branche courante."""
    def run(cmd: list[str]) -> str:
        try:
            return subprocess.check_output(cmd, cwd=PROJECT_DIR, text=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            return f"<error: {e.returncode}>\n{e.output}"

    return {
        "timestamp": now(),
        "branch": run(["git", "branch", "--show-current"]).strip(),
        "status": run(["git", "status", "--short"]),
        "diff_stat": run(["git", "diff", "--stat"]),
        "log": run(["git", "log", "--oneline", "-10"]),
    }


# ---------------------------------------------------------------------------
# Gestion de l'instance unique
# ---------------------------------------------------------------------------

def write_pid() -> None:
    PID_FILE.write_text(str(os.getpid()))


def remove_pid() -> None:
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except OSError:
        pass


def _is_watchdog_process(pid: int) -> bool:
    """Vérifie que le PID correspond bien à ce script."""
    try:
        proc = psutil.Process(pid)
        cmd = " ".join(proc.cmdline() or [])
        return "watchdog_claude_quantlive" in cmd
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def check_single_instance() -> None:
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            if old_pid != os.getpid() and _is_watchdog_process(old_pid):
                print(f"Watchdog déjà en cours (PID {old_pid}). Arrêt.", file=sys.stderr)
                sys.exit(1)
        except (ValueError, OSError):
            pass
    write_pid()


# ---------------------------------------------------------------------------
# Boucle principale
# ---------------------------------------------------------------------------

class Watchdog:
    def __init__(self) -> None:
        self.stop_requested = False
        self.trigger = "manual"
        self.start_time = now()
        self.changes: deque[dict] = deque(maxlen=MAX_CHANGES_IN_MEMORY)
        self.git_snapshots: list[dict] = []
        self.last_git_snapshot = 0.0
        self.codex_missing_since: float | None = None
        self.initial_state: dict | None = None

    def run(self) -> None:
        if not PROJECT_DIR.exists():
            print(f"Dossier introuvable: {PROJECT_DIR}", file=sys.stderr)
            sys.exit(1)

        check_single_instance()

        logger.info("=" * 60)
        logger.info("Watchdog démarré")
        logger.info("Surveillance de %s (sous-dossiers: %s)", PROJECT_DIR, WATCHED_SUBDIRS)
        codex_procs = find_codex_processes()
        logger.info("Processus Claude Code détectés: %s", [p.pid for p in codex_procs])
        logger.info("codex_is_alive() = %s", codex_is_alive())

        initial_git = git_status()
        self.git_snapshots.append(initial_git)
        previous = get_snapshot()
        self.last_git_snapshot = time.monotonic()

        self.initial_state = {
            "timestamp": now(),
            "codex_pids": [p.pid for p in codex_procs],
            "codex_alive": codex_is_alive(),
            "files_tracked": len(previous),
            "git": initial_git,
        }

        logger.info("Snapshot initial pris (%d fichiers)", len(previous))

        cycle = 0
        while True:
            if self.stop_requested:
                self._finish()
                return

            current = get_snapshot()
            previous_set = set(previous.keys())
            current_set = set(current.keys())

            created = current_set - previous_set
            deleted = previous_set - current_set
            modified = {p for p in (previous_set & current_set) if previous[p] != current[p]}

            for p in sorted(created):
                self._log_change("created", p, current[p]["size"])

            for p in sorted(modified):
                self._log_change("modified", p, current[p]["size"])

            for p in sorted(deleted):
                self._log_change("deleted", p)

            previous = current

            now_mono = time.monotonic()

            # Snapshot git périodique
            if now_mono - self.last_git_snapshot >= GIT_SNAPSHOT_INTERVAL:
                self.git_snapshots.append(git_status())
                self.last_git_snapshot = now_mono
                self.git_snapshots = self.git_snapshots[-10:]

            # Heartbeat
            if cycle % HEARTBEAT_CYCLES == 0:
                logger.info("[heartbeat] fichiers=%d changements=%s codex_alive=%s", len(current), len(self.changes), codex_is_alive())

            # Vérifier si Claude Code tourne encore
            if not codex_is_alive():
                if self.codex_missing_since is None:
                    self.codex_missing_since = now_mono
                    logger.info("Claude Code non détecté (confirmation dans %ds)", MIN_CONFIRMATION_SECONDS)
                elif now_mono - self.codex_missing_since >= MIN_CONFIRMATION_SECONDS:
                    logger.info("Claude Code détecté comme arrêté depuis %.0fs -> fin du watchdog", now_mono - self.codex_missing_since)
                    self.trigger = "codex_stopped"
                    self._finish()
                    return
            else:
                if self.codex_missing_since is not None:
                    logger.info("Claude Code est revenu -> reprise de la surveillance")
                self.codex_missing_since = None

            cycle += 1
            sleep(POLL_INTERVAL)

    def _log_change(self, change_type: str, path: str, size: int | None = None) -> None:
        event = {
            "type": change_type,
            "path": path,
            "timestamp": now(),
        }
        if size is not None:
            event["size"] = size
        self.changes.append(event)

        if change_type == "created":
            logger.info("+ %s (%s bytes)", path, size)
        elif change_type == "modified":
            logger.info("* %s (%s bytes)", path, size)
        else:
            logger.info("- %s", path)

    def _finish(self) -> None:
        logger.info("Arrêt du watchdog (%s)", self.trigger)
        summary = {
            "started_at": self.start_time,
            "stopped_at": now(),
            "trigger": self.trigger,
            "total_changes": len(self.changes),
            "changes": list(self.changes),
            "git_snapshots": self.git_snapshots,
            "initial_state": self.initial_state,
        }
        SUMMARY_FILE.write_text(json.dumps(summary, indent=2, default=str))
        logger.info("Résumé sauvegardé dans %s", SUMMARY_FILE)
        remove_pid()
        sys.exit(0)


def main() -> None:
    watchdog = Watchdog()

    def on_signal(signum, frame):
        watchdog.stop_requested = True
        watchdog.trigger = "signal"

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    try:
        watchdog.run()
    except Exception:
        logger.exception("Erreur fatale dans le watchdog")
        remove_pid()
        raise


if __name__ == "__main__":
    main()
