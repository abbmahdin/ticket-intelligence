#!/usr/bin/env bash
# Ticket Intelligence — Single command launcher
# Usage: ./start.sh [setup|up|run|all-test|stop|logs|clean]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log_info()    { echo -e "${GREEN}●${NC} $1"; }
log_warn()    { echo -e "${YELLOW}⚠${NC} $1"; }
log_error()   { echo -e "${RED}✗${NC} $1"; }

usage() {
    echo "=== Ticket Intelligence — Lanceur ==="
    echo ""
    echo "Usage: ./start.sh <command>"
    echo ""
    echo "Commandes:"
    echo "  setup        Installer les dépendances Python"
    echo "  up           Lancer Postgres + Redis (Docker)"
    echo "  run          Démarrer l'API en mode dev"
    echo "  all          Setup + up + run (tout en un)"
    echo "  test         Lancer les tests"
    echo "  stop         Arrêter les services Docker"
    echo "  clean        Tout nettoyer"
    echo "  help         Aide"
    echo ""
    exit 0
}

cmd_setup() {
    log_info "Installation des dépendances Python..."
    python3.12 -m venv .venv >/dev/null 2>&1 || true
    .venv/bin/pip install -e ".[dev]" 2>&1 | tail -1
    log_info "✓ Dépendances installées"
}

cmd_up() {
    log_info "Lancement de Postgres + Redis..."
    docker compose up -d postgres redis 2>&1 | grep -E "Creating|Started|already" || true
    sleep 5
    if docker compose ps | grep -q "postgres.*healthy\|postgres.*running"; then
        log_info "✓ Postgres démarré (localhost:5432)"
    fi
    if docker compose ps | grep -q "redis.*running"; then
        log_info "✓ Redis démarré (localhost:6379)"
    fi
}

cmd_run() {
    log_info "Démarrage de l'API..."
    log_info "  → http://localhost:8000"
    log_info "  → Docs: http://localhost:8000/docs"
    .venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
}

cmd_all() {
    log_info "=== Ticket Intelligence — Mise en route complète ==="
    cmd_setup
    cmd_up
    log_info "✓ Services prêts"
    log_info "Lancement de l'API..."
    .venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
}

cmd_test() {
    log_info "Lancement des tests..."
    .venv/bin/python -m pytest -q
}

cmd_stop() {
    log_info "Arrêt des services..."
    docker compose down
    log_info "✓ Services arrêtés"
}

cmd_clean() {
    log_info "Nettoyage complet..."
    docker compose down -v >/dev/null 2>&1 || true
    rm -rf .venv/ __pycache__/ .pytest_cache/ .ruff_cache/
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    log_info "✓ Nettoyé"
}

cmd_help() { usage; }

# ── Main ────────────────────────────────────────────────────────────────────────
if [ $# -eq 0 ]; then
    usage
fi

case "$1" in
    setup)  cmd_setup ;;
    up)     cmd_up ;;
    run)    cmd_run ;;
    all)    cmd_all ;;
    test)   cmd_test ;;
    stop)   cmd_stop ;;
    clean)  cmd_clean ;;
    help|--help|-h) cmd_help ;;
    *)
        log_error "Commande inconnue: $1"
        usage
        ;;
esac