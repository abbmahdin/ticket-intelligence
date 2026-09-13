"""
Pydantic schemas for the prediction module.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    """Request to predict demand for an event."""

    artist_id: int
    venue_id: int
    event_date: datetime
    artist_popularity: Optional[float] = Field(None, ge=0, le=100)
    venue_capacity: Optional[int] = Field(None, ge=0)


class DemandPrediction(BaseModel):
    """Result of demand prediction."""

    artist_id: int
    venue_id: int
    event_date: datetime
    demand_score: float = Field(..., ge=0, le=1)
    confidence: float = Field(..., ge=0, le=1)
    factors: dict
    predicted_at: datetime = Field(default_factory=datetime.utcnow)


class ModelMetrics(BaseModel):
    """Performance metrics for the prediction model."""

    mae: float = Field(..., ge=0)
    rmse: float = Field(..., ge=0)
    r2_score: float = Field(..., le=1.0)
    sample_count: int = Field(..., ge=0)
    last_trained_at: Optional[datetime] = None


class FeatureImportance(BaseModel):
    """Feature importance scores."""

    feature_name: str
    importance: float
    description: str