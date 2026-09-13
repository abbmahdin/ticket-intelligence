"""Placeholder task module — real tasks are added here as needed."""

from src.workers.scheduler.celery_app import celery_app


@celery_app.task
def sample_task(name: str) -> str:
    return f"hello {name}"
