"""
Test fixtures for Ticket Intelligence.
Uses SQLite in-memory for async tests when Postgres is unavailable,
and mocks for external services.
"""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# Ensure pytest-asyncio uses the auto mode
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def sample_artist_data():
    return {
        "name": "Daft Punk",
        "genre": "Electronic",
        "popularity_score": 95.5,
        "external_id": "tp-001",
    }


@pytest.fixture
def sample_venue_data():
    return {
        "name": "Stade de France",
        "city": "Paris",
        "country": "France",
        "capacity": 80000,
        "external_id": "vn-001",
    }


@pytest.fixture
def sample_event_data(sample_artist_data, sample_venue_data):
    return {
        "title": "Daft Punk Reunion — Paris",
        "artist_id": 1,
        "venue_id": 1,
        "event_date": datetime.utcnow() + timedelta(days=90),
        "demand_score": 0.92,
        "external_id": "ev-001",
        "is_active": True,
    }


@pytest.fixture
def sample_price_record_data():
    return {
        "event_id": 1,
        "platform": "Ticketmaster",
        "price": 89.50,
        "currency": "EUR",
    }


@pytest.fixture
def sample_alert_data():
    return {
        "user_email": "fan@example.com",
        "event_id": 1,
        "alert_type": "price_drop",
        "threshold_value": 70.00,
        "is_active": True,
        "is_triggered": False,
    }


@pytest.fixture
def sample_legal_queue_data():
    return {
        "event_id": 1,
        "platform": "Ticketmaster",
        "listing_url": "https://ticketmaster.fr/event/daft-punk",
        "price": 89.50,
        "currency": "EUR",
        "verified": False,
    }


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest.fixture
def mock_httpx_client():
    """Mock HTTP client for external API calls."""
    client_mock = AsyncMock()
    return client_mock


@pytest.fixture
def mock_celery_task():
    """Mock Celery task dispatch."""
    return MagicMock()


@pytest.fixture
def mock_demand_model():
    """Mock ML model for prediction tests."""
    model_mock = MagicMock()
    model_mock.predict = MagicMock(return_value=0.85)
    model_mock.predict_proba = MagicMock(return_value=[[0.15, 0.85]])
    return model_mock