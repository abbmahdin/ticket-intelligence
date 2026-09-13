"""
Minimal Celery app scaffold so docker-compose can start the worker/beat
containers.  Real task definitions are added as the project matures.
"""

from celery import Celery

from src.config import settings

celery_app = Celery(
    "ticket-intelligence",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.workers.scheduler.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task
def debug_task():
    return "pong"
