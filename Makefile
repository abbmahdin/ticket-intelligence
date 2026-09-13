# Makefile pour Ticket Intelligence
# Usage: make help | make setup | make up | make run | make test | make stop

help:
	@echo "=== Ticket Intelligence — Commandes disponibles ==="
	@echo "  make setup      Installer les dépendances Python"
	@echo "  make up         Lancer Postgres + Redis (Docker)"
	@echo "  make run        Démarrer l'API en mode dev"
	@echo "  make test       Lancer les tests pytest"
	@echo "  make stop       Arrêter tous les services"
	@echo "  make logs       Voir les logs de l'API"
	@echo "  make clean      Nettoyer les contenus"`

.PHONY: setup up run test stop logs clean

setup:
	python3.12 -m venv .venv
	.venv/bin/pip install -e ".[dev]"
	@echo "✓ Python dépendances installées"

up:
	docker compose up -d postgres redis
	@echo "✓ Postgres + Redis démarrés"
	@echo "  Postgres:  localhost:5432"
	@echo "  Redis:     localhost:6379"

run:
	.venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
	@echo "✓ API disponible sur http://localhost:8000"

test:
	.venv/bin/python -m pytest -q

stop:
	docker compose down
	@echo "✓ Tous les services arrêtés"

logs:
	docker compose logs -f api

clean:
	docker compose down -v
	rm -rf .venv/ __pycache__/ .pytest_cache/ .ruff_cache/
	find . -name "*.pyc" -delete
	rm -rf src/**/__pycache__/ tests/**/__pycache__/
	@echo "✓ Nettoyage complet"