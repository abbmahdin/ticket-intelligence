"""
Tests for the comparator module.
"""
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.modules.comparator.service import ComparatorService
from src.modules.comparator.schemas import (
    ComparisonRequest,
    ComparisonResult,
    PlatformPrice,
    PriceAnomaly,
)


class TestComparisonRequest:
    """Tests for creating comparison requests."""

    def test_valid_request_with_event_id(self):
        """Should create a valid comparison request."""
        req = ComparisonRequest(event_id=1)
        assert req.event_id == 1

    def test_valid_request_with_filters(self):
        """Should accept section and quantity filters."""
        req = ComparisonRequest(event_id=1, section="Orchestra", quantity=2)
        assert req.section == "Orchestra"
        assert req.quantity == 2


class TestPriceComparison:
    """Tests for comparing prices across platforms."""

    @pytest.fixture
    def comparator_service(self, mock_redis):
        return ComparatorService(redis=mock_redis)

    @pytest.mark.asyncio
    async def test_compare_prices_across_platforms(self, comparator_service):
        """Should compare prices from multiple platforms."""
        request = ComparisonRequest(event_id=1)

        result = await comparator_service.compare(request)

        assert isinstance(result, ComparisonResult)
        assert result.event_id == 1
        assert isinstance(result.platform_prices, list)
        assert result.lowest_price is not None or len(result.platform_prices) == 0

    @pytest.mark.asyncio
    async def test_identify_lowest_price(self, comparator_service):
        """Should identify the lowest available price."""
        request = ComparisonRequest(event_id=1)
        mock_prices = [
            PlatformPrice(platform="Ticketmaster", price=89.50, currency="EUR"),
            PlatformPrice(platform="StubHub", price=95.00, currency="EUR"),
            PlatformPrice(platform="Viagogo", price=110.00, currency="EUR"),
        ]

        result = await comparator_service._rank_prices(mock_prices)

        assert result.lowest_price == 89.50
        assert result.highest_price == 110.00

    @pytest.mark.asyncio
    async def test_rank_prices_lowest_first(self, comparator_service):
        """Should rank prices from lowest to highest."""
        mock_prices = [
            PlatformPrice(platform="StubHub", price=95.00, currency="EUR"),
            PlatformPrice(platform="Ticketmaster", price=89.50, currency="EUR"),
            PlatformPrice(platform="Viagogo", price=110.00, currency="EUR"),
        ]

        ranked = await comparator_service._rank_prices(mock_prices)

        assert ranked.ranked_prices[0].price <= ranked.ranked_prices[1].price
        assert ranked.ranked_prices[1].price <= ranked.ranked_prices[2].price

    @pytest.mark.asyncio
    async def test_handle_no_listings(self, comparator_service):
        """Should handle case with no available listings."""
        request = ComparisonRequest(event_id=999)

        result = await comparator_service.compare(request)

        assert result.platform_prices == []
        assert result.lowest_price is None
        assert result.highest_price is None


class TestPriceAnomalyDetection:
    """Tests for detecting anomalous prices."""

    @pytest.fixture
    def comparator_service(self, mock_redis):
        return ComparatorService(redis=mock_redis)

    @pytest.mark.asyncio
    async def test_detect_price_anomaly(self, comparator_service):
        """Should flag prices that deviate significantly from market average."""
        prices = [50.0, 55.0, 52.0, 48.0, 200.0]  # 200 is anomalous

        anomalies = await comparator_service.detect_anomalies(prices)

        assert len(anomalies) >= 1
        assert anomalies[0].price == 200.0
        assert anomalies[0].deviation > 2.0  # more than 2 std devs

    @pytest.mark.asyncio
    async def test_no_anomalies_in_normal_prices(self, comparator_service):
        """Should not flag normal prices as anomalous."""
        prices = [50.0, 51.0, 49.0, 52.0, 48.0, 50.0]

        anomalies = await comparator_service.detect_anomalies(prices)

        assert len(anomalies) == 0

    @pytest.mark.asyncio
    async def test_insufficient_data_for_anomaly_detection(self, comparator_service):
        """Should return empty list with insufficient data."""
        anomalies = await comparator_service.detect_anomalies([50.0])
        assert anomalies == []


class TestPlatformLegitimacy:
    """Tests for verifying platform legitimacy."""

    def test_authorized_platform_recognized(self):
        """Should recognize authorized resale platforms."""
        service = ComparatorService()
        authorized = ["Ticketmaster", "StubHub", "Viagogo", "SeatGeek"]

        for platform in authorized:
            assert service.is_authorized_platform(platform) is True

    def test_unknown_platform_flagged(self):
        """Should flag unknown platforms."""
        service = ComparatorService()
        assert service.is_authorized_platform("UnknownScamSite") is False