"""
Tests for the prediction module (ML-based demand scoring).
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.modules.prediction.service import PredictionService
from src.modules.prediction.schemas import (
    DemandPrediction,
    PredictionRequest,
    ModelMetrics,
)


class TestPredictionRequest:
    """Tests for creating prediction requests."""

    def test_valid_request_with_all_fields(self):
        """Should create a valid prediction request."""
        req = PredictionRequest(
            artist_id=1,
            venue_id=1,
            event_date=datetime.utcnow() + timedelta(days=30),
        )
        assert req.artist_id == 1
        assert req.venue_id == 1

    def test_valid_request_with_optional_fields(self):
        """Should accept optional artist popularity and venue capacity."""
        req = PredictionRequest(
            artist_id=1,
            venue_id=1,
            event_date=datetime.utcnow() + timedelta(days=30),
            artist_popularity=95.0,
            venue_capacity=50000,
        )
        assert req.artist_popularity == 95.0
        assert req.venue_capacity == 50000


class TestDemandPrediction:
    """Tests for demand prediction results."""

    def test_valid_prediction(self):
        """Should create a valid demand prediction."""
        pred = DemandPrediction(
            artist_id=1,
            venue_id=1,
            event_date=datetime.utcnow(),
            demand_score=0.85,
            confidence=0.78,
            factors={"artist_popularity": 0.4, "venue_size": 0.3},
        )
        assert 0.0 <= pred.demand_score <= 1.0
        assert 0.0 <= pred.confidence <= 1.0

    def test_demand_score_clamped_to_range(self):
        """Should reject demand_score outside [0, 1]."""
        with pytest.raises(ValueError):
            DemandPrediction(
                artist_id=1,
                venue_id=1,
                event_date=datetime.utcnow(),
                demand_score=1.5,
                confidence=0.5,
            )


class TestPredictionService:
    """Tests for the prediction service."""

    @pytest.fixture
    def prediction_service(self, mock_demand_model, mock_redis):
        return PredictionService(model=mock_demand_model, redis=mock_redis)

    @pytest.mark.asyncio
    async def test_predict_demand(self, prediction_service):
        """Should return a demand score between 0 and 1."""
        request = PredictionRequest(
            artist_id=1,
            venue_id=1,
            event_date=datetime.utcnow() + timedelta(days=30),
            artist_popularity=95.0,
            venue_capacity=80000,
        )

        result = await prediction_service.predict(request)

        assert 0.0 <= result.demand_score <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_prediction_uses_features(self, prediction_service):
        """Should build feature vector from request."""
        request = PredictionRequest(
            artist_id=1,
            venue_id=1,
            event_date=datetime.utcnow() + timedelta(days=30),
            artist_popularity=95.0,
            venue_capacity=80000,
        )

        features = prediction_service._build_features(request)

        assert "artist_popularity" in features
        assert "venue_capacity" in features
        assert "days_until_event" in features

    @pytest.mark.asyncio
    async def test_prediction_includes_factors(self, prediction_service):
        """Should return explanation of factors."""
        request = PredictionRequest(
            artist_id=1,
            venue_id=1,
            event_date=datetime.utcnow() + timedelta(days=30),
        )

        result = await prediction_service.predict(request)

        assert isinstance(result.factors, dict)
        assert len(result.factors) > 0

    @pytest.mark.asyncio
    async def test_prediction_caching(self, prediction_service, mock_redis):
        """Should cache prediction result."""
        request = PredictionRequest(
            artist_id=1,
            venue_id=1,
            event_date=datetime.utcnow() + timedelta(days=30),
        )

        await prediction_service.predict(request)

        # Should cache result
        mock_redis.setex.assert_called()

    @pytest.mark.asyncio
    async def test_predict_batch(self, prediction_service):
        """Should predict demand for multiple events."""
        requests = [
            PredictionRequest(artist_id=1, venue_id=1, event_date=datetime.utcnow() + timedelta(days=30)),
            PredictionRequest(artist_id=2, venue_id=1, event_date=datetime.utcnow() + timedelta(days=45)),
        ]

        results = await prediction_service.predict_batch(requests)

        assert len(results) == 2
        assert all(isinstance(r, DemandPrediction) for r in results)


class TestModelMetrics:
    """Tests for model performance metrics."""

    def test_metrics_with_valid_values(self):
        """Should create metrics with valid values."""
        metrics = ModelMetrics(
            mae=0.05,
            rmse=0.07,
            r2_score=0.85,
            sample_count=1000,
        )
        assert metrics.mae == 0.05
        assert metrics.r2_score == 0.85

    def test_metrics_r2_score_in_valid_range(self):
        """Should reject invalid R² score."""
        with pytest.raises(ValueError):
            ModelMetrics(mae=0.05, rmse=0.07, r2_score=1.5, sample_count=100)


class TestFeatureEngineering:
    """Tests for feature extraction."""

    def test_build_features_from_request(self):
        """Should extract all required features from request."""
        service = PredictionService()
        request = PredictionRequest(
            artist_id=1,
            venue_id=1,
            event_date=datetime.utcnow() + timedelta(days=60),
            artist_popularity=80.0,
            venue_capacity=50000,
        )

        features = service._build_features(request)

        assert isinstance(features, dict)
        assert features["artist_popularity"] == 80.0
        assert features["venue_capacity"] == 50000
        assert features["days_until_event"] >= 59  # approximately 60

    def test_features_with_defaults(self):
        """Should provide defaults for optional fields."""
        service = PredictionService()
        request = PredictionRequest(
            artist_id=1,
            venue_id=1,
            event_date=datetime.utcnow() + timedelta(days=30),
        )

        features = service._build_features(request)

        assert features["artist_popularity"] == 50.0  # default
        assert features["venue_capacity"] == 10000  # default