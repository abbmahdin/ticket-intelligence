"""
Prediction module — ML-based demand scoring using scikit-learn.
"""
from src.modules.prediction.router import router as prediction_router
from src.modules.prediction.service import PredictionService

__all__ = ["PredictionService", "prediction_router"]
