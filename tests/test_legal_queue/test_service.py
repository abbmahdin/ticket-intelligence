"""
Tests for the legal-queue module.
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.modules.legal_queue.service import LegalQueueService
from src.modules.legal_queue.schemas import (
    SellerListing,
    QueueItemCreate,
    QueueItemResponse,
    PlatformStatus,
    SyncResult,
)


class TestQueueItemCreate:
    """Tests for creating queue items."""

    def test_valid_queue_item(self):
        """Should create a valid queue item."""
        item = QueueItemCreate(
            event_id=1,
            platform="Ticketmaster",
            listing_url="https://ticketmaster.fr/event/123",
            price=89.50,
            currency="EUR",
            section="Orchestra",
            quantity=2,
        )
        assert item.platform == "Ticketmaster"
        assert item.price == 89.50

    def test_url_must_be_valid(self):
        """Should reject invalid URLs."""
        with pytest.raises(ValueError):
            QueueItemCreate(
                event_id=1,
                platform="Ticketmaster",
                listing_url="not-a-url",
                price=89.50,
            )

    def test_price_must_be_positive(self):
        """Should reject negative prices."""
        with pytest.raises(ValueError):
            QueueItemCreate(
                event_id=1,
                platform="Ticketmaster",
                listing_url="https://ticketmaster.fr/event/123",
                price=-10.0,
            )


class TestLegalQueueService:
    """Tests for the legal queue service."""

    @pytest.fixture
    def queue_service(self, mock_redis, mock_httpx_client):
        return LegalQueueService(
            redis=mock_redis,
            http_client=mock_httpx_client,
        )

    @pytest.mark.asyncio
    async def test_add_listing_to_queue(self, queue_service):
        """Should add a verified listing to the queue."""
        listing = QueueItemCreate(
            event_id=1,
            platform="Ticketmaster",
            listing_url="https://ticketmaster.fr/event/123",
            price=89.50,
            currency="EUR",
        )

        result = await queue_service.add_listing(listing)

        assert result.event_id == 1
        assert result.platform == "Ticketmaster"
        assert result.verified is True

    @pytest.mark.asyncio
    async def test_reject_unauthorized_platform(self, queue_service):
        """Should reject listings from unauthorized platforms."""
        listing = QueueItemCreate(
            event_id=1,
            platform="FakeScamSite",
            listing_url="https://fakescam.com/event",
            price=50.00,
        )

        with pytest.raises(ValueError, match="unauthorized platform"):
            await queue_service.add_listing(listing)

    @pytest.mark.asyncio
    async def test_verify_listing(self, queue_service):
        """Should verify a listing URL is accessible."""
        result = await queue_service.verify_listing(
            "https://ticketmaster.fr/event/123"
        )
        assert result.is_accessible is True
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_verify_listing_rate_limited(self, queue_service):
        """Should respect rate limits when verifying."""
        result = await queue_service.verify_listing(
            "https://ticketmaster.fr/event/123",
            respect_rate_limit=True,
        )
        assert result.respects_rate_limit is True

    @pytest.mark.asyncio
    async def test_get_queue_status(self, queue_service):
        """Should return current queue status."""
        status = await queue_service.get_queue_status(event_id=1)

        assert status.event_id == 1
        assert hasattr(status, "total_items")
        assert hasattr(status, "verified_items")
        assert hasattr(status, "platforms")

    @pytest.mark.asyncio
    async def test_list_event_listings(self, queue_service):
        """Should list all queue items for an event."""
        items = await queue_service.list_event_items(event_id=1)

        assert isinstance(items, list)


class TestPlatformIntegration:
    """Tests for platform API integrations."""

    @pytest.fixture
    def queue_service(self, mock_redis, mock_httpx_client):
        return LegalQueueService(
            redis=mock_redis,
            http_client=mock_httpx_client,
        )

    @pytest.mark.asyncio
    async def test_sync_ticketmaster_api(self, queue_service):
        """Should sync listings from Ticketmaster API."""
        result = await queue_service.sync_platform("Ticketmaster", event_id=1)

        assert isinstance(result, SyncResult)
        assert result.platform == "Ticketmaster"
        assert result.items_synced >= 0

    @pytest.mark.asyncio
    async def test_sync_respects_rate_limit(self, queue_service):
        """Should respect API rate limits during sync."""
        result = await queue_service.sync_platform(
            "Ticketmaster", event_id=1, max_requests_per_minute=30
        )

        assert result.rate_limit_respected is True

    @pytest.mark.asyncio
    async def test_sync_with_robots_txt_check(self, queue_service):
        """Should check robots.txt before scraping."""
        result = await queue_service.sync_platform(
            "Ticketmaster", event_id=1, check_robots_txt=True
        )

        assert result.robots_txt_checked is True

    @pytest.mark.asyncio
    async def test_platform_health_check(self, queue_service):
        """Should check if platform API is healthy."""
        health = await queue_service.check_platform_health("Ticketmaster")

        assert isinstance(health, PlatformStatus)
        assert health.platform == "Ticketmaster"
        assert health.is_accessible is True


class TestSellerListing:
    """Tests for seller listing model."""

    def test_valid_seller_listing(self):
        """Should create a valid seller listing."""
        listing = SellerListing(
            platform="Ticketmaster",
            event_id=1,
            listing_url="https://ticketmaster.fr/event/123",
            price=89.50,
            currency="EUR",
            face_value=75.00,
            is_official=True,
        )
        assert listing.is_official is True
        assert listing.face_value == 75.00

    def test_premium_calculation(self):
        """Should calculate premium over face value."""
        listing = SellerListing(
            platform="Ticketmaster",
            event_id=1,
            listing_url="https://ticketmaster.fr/event/123",
            price=100.00,
            face_value=75.00,
        )
        assert listing.premium_percent == pytest.approx(33.33, rel=0.01)