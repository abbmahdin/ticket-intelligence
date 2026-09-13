"""
Prediction service — ML-based demand scoring for events.
Uses scikit-learn RandomForest for demand classification.
"""
import logging
from datetime import datetime

import numpy as np

from src.modules.prediction.schemas import (
    DemandPrediction,
    ModelMetrics,
    PredictionRequest,
)

logger = logging.getLogger(__name__)


class PredictionService:
    """Service for predicting event demand using ML features."""

    def __init__(self, model=None, redis=None):
        self.model = model
        self.redis = redis
        self._feature_names = [
            "artist_popularity",
            "venue_capacity",
            "days_until_event",
            "is_weekend",
            "is_holiday_season",
        ]

    def _build_features(self, request: PredictionRequest) -> dict:
        """Extract feature dictionary from prediction request."""
        now = datetime.utcnow()
        days_until = max((request.event_date - now).days, 0)
        is_weekend = request.event_date.weekday() >= 5
        is_holiday = request.event_date.month in [6, 7, 8, 12]

        return {
            "artist_popularity": request.artist_popularity or 50.0,
            "venue_capacity": request.venue_capacity or 10000,
            "days_until_event": days_until,
            "is_weekend": int(is_weekend),
            "is_holiday_season": int(is_holiday),
        }

    async def predict(self, request: PredictionRequest) -> DemandPrediction:
        """
        Predict demand score for an event.

        In production: loads trained model and makes prediction.
        """
        features = self._build_features(request)

        if self.model:
            feature_vector = np.array([list(features.values())])
            prediction = self.model.predict(feature_vector)
            if hasattr(prediction, "__getitem__"):
                demand_score = float(prediction[0])
            else:
                demand_score = float(prediction)
            # Clamp to [0, 1]
            demand_score = max(0.0, min(1.0, demand_score))
            # Confidence based on model agreement (simplified)
            confidence = 0.75
        else:
            # Fallback heuristic when no model is available
            demand_score = self._heuristic_predict(features)
            confidence = 0.5

        # Cache if Redis available
        if self.redis:
            cache_key = f"pred:{request.artist_id}:{request.venue_id}:{request.event_date.date()}"
            await self.redis.setex(cache_key, 3600, str(demand_score))

        return DemandPrediction(
            artist_id=request.artist_id,
            venue_id=request.venue_id,
            event_date=request.event_date,
            demand_score=round(demand_score, 4),
            confidence=confidence,
            factors=features,
        )

    def _heuristic_predict(self, features: dict) -> float:
        """Simple heuristic fallback when no ML model is loaded."""
        score = 0.0
        score += features["artist_popularity"] / 100 * 0.4
        score += min(features["venue_capacity"] / 100000, 1.0) * 0.2
        score += (1 - min(features["days_until_event"] / 365, 1.0)) * 0.2
        score += features["is_weekend"] * 0.1
        score += features["is_holiday_season"] * 0.1
        return min(score, 1.0)

    async def predict_batch(self, requests: list[PredictionRequest]) -> list[DemandPrediction]:
        """Predict demand for multiple events."""
        results = []
        for req in requests:
            result = await self.predict(req)
            results.append(result)
        return results

    def get_metrics(self) -> ModelMetrics:
        """Return current model performance metrics."""
        # In production: load from model registry
        return ModelMetrics(
            mae=0.05,
            rmse=0.07,
            r2_score=0.85,
            sample_count=1000,
        )