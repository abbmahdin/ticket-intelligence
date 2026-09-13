"""
FastAPI router for the prediction module.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from src.modules.prediction.schemas import (
    DemandPrediction,
    ModelMetrics,
    PredictionRequest,
)
from src.modules.prediction.service import PredictionService

router = APIRouter(prefix="/prediction", tags=["prediction"])

_service = PredictionService()


@router.post("/predict", response_model=DemandPrediction)
async def predict_demand(request: PredictionRequest):
    """Predict demand score for a specific artist/venue/date combination."""
    if request.event_date <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Event date must be in the future")
    return await _service.predict(request)


@router.post("/predict/batch", response_model=list[DemandPrediction])
async def predict_batch(requests: list[PredictionRequest]):
    """Predict demand for multiple events."""
    return await _service.predict_batch(requests)


@router.get("/metrics", response_model=ModelMetrics)
async def get_model_metrics():
    """Get current model performance metrics."""
    return _service.get_metrics()


@router.get("/health")
async def prediction_health():
    """Check if prediction service is operational."""
    return {"status": "ok", "model_loaded": _service.model is not None}