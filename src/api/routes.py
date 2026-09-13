"""
API route aggregation for Ticket Intelligence.

Mounts every module router and exposes a global health endpoint.
"""

from fastapi import APIRouter

from src.api import health
from src.modules.alerts.router import router as alerts_router
from src.modules.analysis.router import router as analysis_router
from src.modules.comparator.router import router as comparator_router
from src.modules.legal_queue.router import router as legal_queue_router
from src.modules.prediction.router import router as prediction_router

api = APIRouter()
api.include_router(prediction_router)
api.include_router(analysis_router)
api.include_router(comparator_router)
api.include_router(legal_queue_router)
api.include_router(alerts_router)
api.include_router(health.router)


@api.get("/health")
async def aggregated_health():
    """Aggregate health across all mounted modules."""
    return {
        "status": "ok",
        "modules": {
            "prediction": "mounted",
            "analysis": "mounted",
            "comparator": "mounted",
            "legal-queue": "mounted",
            "alerts": "mounted",
        },
    }
