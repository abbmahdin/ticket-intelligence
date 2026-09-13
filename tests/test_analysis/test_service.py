"""
Tests for the analysis module.
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.modules.analysis.service import AnalysisService
from src.modules.analysis.schemas import (
    HistoricalPriceQuery,
    PriceStatistics,
    PriceTrend,
)


class TestHistoricalPriceQuery:
    """Tests for querying historical price data."""

    def test_valid_query_with_event_id(self):
        """Should create a valid query with event_id."""
        query = HistoricalPriceQuery(
            event_id=1,
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
        )
        assert query.event_id == 1

    def test_valid_query_with_artist_id(self):
        """Should create a valid query with artist_id."""
        query = HistoricalPriceQuery(artist_id=42)
        assert query.artist_id == 42

    def test_valid_query_with_platform_filter(self):
        """Should accept platform filter."""
        query = HistoricalPriceQuery(event_id=1, platform="Ticketmaster")
        assert query.platform == "Ticketmaster"

    def test_date_range_validation(self):
        """Should reject end_date before start_date."""
        with pytest.raises(ValueError):
            HistoricalPriceQuery(
                event_id=1,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() - timedelta(days=10),
            )


class TestPriceStatistics:
    """Tests for computing price statistics."""

    @pytest.fixture
    def analysis_service(self, mock_redis):
        return AnalysisService(redis=mock_redis)

    @pytest.mark.asyncio
    async def test_compute_statistics(self, analysis_service):
        """Should compute min, max, avg, median, std from price data."""
        prices = [50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0]

        stats = await analysis_service.compute_statistics(prices)

        assert stats.min_price == 50.0
        assert stats.max_price == 80.0
        assert stats.avg_price == 65.0
        assert stats.median_price == 65.0
        assert stats.count == 7

    @pytest.mark.asyncio
    async def test_compute_statistics_empty_list(self, analysis_service):
        """Should handle empty price list gracefully."""
        stats = await analysis_service.compute_statistics([])

        assert stats.count == 0
        assert stats.min_price is None
        assert stats.avg_price is None

    @pytest.mark.asyncio
    async def test_compute_statistics_single_price(self, analysis_service):
        """Should handle single price point."""
        stats = await analysis_service.compute_statistics([99.99])

        assert stats.count == 1
        assert stats.min_price == 99.99
        assert stats.max_price == 99.99
        assert stats.avg_price == 99.99
        assert stats.std_deviation == 0.0


class TestPriceTrend:
    """Tests for price trend analysis."""

    @pytest.fixture
    def analysis_service(self, mock_redis):
        return AnalysisService(redis=mock_redis)

    @pytest.mark.asyncio
    async def test_detect_upward_trend(self, analysis_service):
        """Should detect upward price trend."""
        price_points = [
            {"date": datetime.utcnow() - timedelta(days=6), "price": 50.0},
            {"date": datetime.utcnow() - timedelta(days=5), "price": 55.0},
            {"date": datetime.utcnow() - timedelta(days=4), "price": 60.0},
            {"date": datetime.utcnow() - timedelta(days=3), "price": 65.0},
            {"date": datetime.utcnow() - timedelta(days=2), "price": 70.0},
            {"date": datetime.utcnow() - timedelta(days=1), "price": 75.0},
            {"date": datetime.utcnow(), "price": 80.0},
        ]

        trend = await analysis_service.detect_trend(price_points)

        assert trend.direction == "upward"
        assert trend.slope > 0
        assert trend.change_percent > 0

    @pytest.mark.asyncio
    async def test_detect_downward_trend(self, analysis_service):
        """Should detect downward price trend."""
        price_points = [
            {"date": datetime.utcnow() - timedelta(days=6), "price": 80.0},
            {"date": datetime.utcnow() - timedelta(days=5), "price": 75.0},
            {"date": datetime.utcnow() - timedelta(days=4), "price": 70.0},
            {"date": datetime.utcnow() - timedelta(days=3), "price": 65.0},
            {"date": datetime.utcnow() - timedelta(days=2), "price": 60.0},
            {"date": datetime.utcnow() - timedelta(days=1), "price": 55.0},
            {"date": datetime.utcnow(), "price": 50.0},
        ]

        trend = await analysis_service.detect_trend(price_points)

        assert trend.direction == "downward"
        assert trend.slope < 0
        assert trend.change_percent < 0

    @pytest.mark.asyncio
    async def test_detect_stable_trend(self, analysis_service):
        """Should detect stable prices."""
        price_points = [
            {"date": datetime.utcnow() - timedelta(days=i), "price": 65.0}
            for i in range(7)
        ]

        trend = await analysis_service.detect_trend(price_points)

        assert trend.direction == "stable"
        assert abs(trend.slope) < 0.01

    @pytest.mark.asyncio
    async def test_trend_with_insufficient_data(self, analysis_service):
        """Should handle insufficient data points."""
        price_points = [{"date": datetime.utcnow(), "price": 50.0}]

        trend = await analysis_service.detect_trend(price_points)

        assert trend.direction == "insufficient_data"
        assert trend.slope == 0.0


class TestMarketSummary:
    """Tests for market summary generation."""

    @pytest.fixture
    def analysis_service(self, mock_redis):
        return AnalysisService(redis=mock_redis)

    @pytest.mark.asyncio
    async def test_generate_market_summary(self, analysis_service):
        """Should generate a market summary for an event."""
        summary = await analysis_service.get_market_summary(event_id=1)

        assert summary.event_id == 1
        assert hasattr(summary, "current_lowest_price")
        assert hasattr(summary, "current_highest_price")
        assert hasattr(summary, "average_price")
        assert hasattr(summary, "total_listings")
        assert hasattr(summary, "trend_direction")

    @pytest.mark.asyncio
    async def test_cache_market_summary(self, analysis_service, mock_redis):
        """Should cache market summary in Redis."""
        await analysis_service.get_market_summary(event_id=1)

        mock_redis.setex.assert_called_once()
        # Verify TTL is reasonable (5 minutes = 300 seconds)
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 300