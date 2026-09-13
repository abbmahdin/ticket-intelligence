# Ticket Intelligence

API FastAPI pour la prédiction de la demande de billets, l'analyse des prix de revente,
la comparaison cross-plateformes, la gestion d'une file de conformité légale et
les notifications d'alertes pour le marché secondaire des billets.

## Stack technique

| Couche | Technologie |
|---|---|
| API | FastAPI (Python 3.12) |
| ORM | SQLAlchemy (async) |
| Base de données | PostgreSQL 16 |
| Cache / Broker | Redis 7 |
| Tâches asynchrones | Celery |
| Tests | pytest |

## Prérequis

- Python 3.12+
- Docker & Docker Compose (optionnel — pour lancer Postgres + Redis)
- Une base PostgreSQL et un Redis accessibles (ou via Docker)

## Installation

```bash
# 1. Cloner / se placer dans le projet
cd ticket-intelligence

# 2. Créer l'environnement virtuel (si ce n'est pas déjà fait)
python -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 3. Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos valeurs (DB, Redis, API keys…)

# 4. Lancer les services (Postgres + Redis) via Docker
docker compose up -d postgres redis

# 5. Lancer l'API
.venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

L'API est disponible sur http://localhost:8000.
La documentation interactive : http://localhost:8000/docs.

## Endpoints API

### Health

| Méthode | Chemin | Description |
|---|---|---|
| `GET` | `/` | Informations sur le service |
| `GET` | `/health` | État de santé agrégé |

### Prediction

| Méthode | Chemin | Description |
|---|---|---|
| `POST` | `/prediction/predict` | Prédire la demande pour un événement |
| `POST` | `/prediction/predict/batch` | Prédictions en batch |
| `GET` | `/prediction/metrics` | Métriques du modèle |
| `GET` | `/prediction/health` | Santé du service de prédiction |

### Analysis

| Méthode | Chemin | Description |
|---|---|---|
| `GET` | `/analysis/statistics/{event_id}` | Statistiques de prix (min, max, avg, médiane, écart-type) |
| `GET` | `/analysis/trend/{event_id}` | Tendance des prix (upward/downward/stable) |
| `GET` | `/analysis/market-summary/{event_id}` | Résumé marché complet |
| `GET` | `/analysis/events` | Liste des événements monitorés |

### Comparator

| Méthode | Chemin | Description |
|---|---|---|
| `POST` | `/comparator/compare` | Comparer les prix entre plateformes autorisées |
| `GET` | `/comparator/platforms` | Liste des plateformes autorisées |
| `GET` | `/comparator/platforms/{platform_name}` | Note d'une plateforme spécifique |

### Legal Queue

| Méthode | Chemin | Description |
|---|---|---|
| `POST` | `/legal-queue/items` | Ajouter une listing à la file légale |
| `GET` | `/legal-queue/items` | Lister les items (filtre par event_id) |
| `GET` | `/legal-queue/status/{event_id}` | Statut de la file pour un événement |
| `POST` | `/legal-queue/sync/{platform}` | Synchroniser les listings d'une plateforme |
| `GET` | `/legal-queue/platforms` | Liste des plateformes autorisées |
| `GET` | `/legal-queue/platforms/{platform_name}/health` | Santé de l'API d'une plateforme |

### Alerts

| Méthode | Chemin | Description |
|---|---|---|
| `POST` | `/alerts/` | Créer une règle d'alerte |
| `GET` | `/alerts/` | Lister les règles (filtre par user_email) |
| `GET` | `/alerts/{alert_id}` | Détails d'une règle |
| `PATCH` | `/alerts/{alert_id}` | Mettre à jour une règle |
| `DELETE` | `/alerts/{alert_id}` | Supprimer une règle |

## Exemples curl

### Prédire la demande

```bash
curl -X POST http://localhost:8000/prediction/predict \
  -H "Content-Type: application/json" \
  -d '{
    "artist_id": 42,
    "venue_id": 7,
    "event_date": "2027-06-15T20:00:00",
    "artist_popularity": 85.0,
    "venue_capacity": 20000
  }'
```

### Statistiques de prix

```bash
curl http://localhost:8000/analysis/statistics/1001?platform=StubHub
```

### Comparer les prix

```bash
curl -X POST http://localhost:8000/comparator/compare \
  -H "Content-Type: application/json" \
  -d '{"event_id": 1001, "section": "Orchestra", "quantity": 2}'
```

### Créer une alerte

```bash
curl -X POST http://localhost:8000/alerts/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "fan@example.com",
    "event_id": 1001,
    "alert_type": "price_drop",
    "threshold_price": 50.0,
    "notification_channel": "email"
  }'
```

## Tests

```bash
.venv/bin/python -m pytest -q
```

La suite couvre les modules de prédiction, analyse, comparateur, file légale et alertes.

## Structure du projet

```
ticket-intelligence/
├── src/
│   ├── main.py              # Point d'entrée FastAPI
│   ├── api/
│   │   ├── routes.py        # Aggregation des routers
│   │   ├── health.py        # Health-check léger
│   │   └── __init__.py
│   ├── config.py            # Configuration (Pydantic Settings)
│   ├── database.py          # Engine + sessions SQLAlchemy
│   ├── schemas.py           # Schemas Pydantic partagés
│   ├── modules/
│   │   ├── prediction/      # Prédiction de demande
│   │   ├── analysis/        # Analyse de prix
│   │   ├── comparator/      # Comparateur cross-plateformes
│   │   ├── legal_queue/     # File de conformité légale
│   │   └── alerts/          # Règles d'alerte et notifications
│   └── workers/
│       └── scheduler/       # Celery app + tasks
├── tests/
├── docker-compose.yml
├── Dockerfile
├── .env
└── pyproject.toml
```

## Licence

Propriétaire — tous droits réservés.
