# Ticket Intelligence — Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Code
COPY . .

# Exposition
EXPOSE 8000

# Commande par défaut (écrasée par docker-compose)
CMD ["uvicorn", "src.api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
