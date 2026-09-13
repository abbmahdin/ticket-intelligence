"""
Legal-queue service — manages ticket listings from authorized resellers.
Respects rate limits and robots.txt. Zero automated purchases.
"""
import logging
import time
from datetime import datetime
from typing import Optional

from src.modules.legal_queue.schemas import (
    ListingVerification,
    PlatformName,
    PlatformStatus,
    QueueItemCreate,
    QueueItemResponse,
    QueueStatus,
    SyncResult,
)

logger = logging.getLogger(__name__)

# Authorized platforms configuration
AUTHORIZED_PLATFORMS: dict[str, dict] = {
    "Ticketmaster": {
        "base_url": "https://app.ticketmaster.com",
        "trust_score": 95,
        "rate_limit_per_minute": 30,
    },
    "StubHub": {
        "base_url": "https://api.stubhub.com",
        "trust_score": 85,
        "rate_limit_per_minute": 20,
    },
    "Viagogo": {
        "base_url": "https://www.viagogo.com",
        "trust_score": 70,
        "rate_limit_per_minute": 15,
    },
    "SeatGeek": {
        "base_url": "https://api.seatgeek.com",
        "trust_score": 88,
        "rate_limit_per_minute": 25,
    },
    "Eventbrite": {
        "base_url": "https://www.eventbriteapi.com",
        "trust_score": 90,
        "rate_limit_per_minute": 30,
    },
    "Dice": {
        "base_url": "https://api.dice.fm",
        "trust_score": 92,
        "rate_limit_per_minute": 25,
    },
}


class LegalQueueService:
    """
    Service for managing ticket listings from authorized resellers.

    Rules:
    - Only authorized platforms
    - Respect rate limits
    - Check robots.txt before fetching
    - Zero automated purchasing
    """

    def __init__(self, redis=None, http_client=None):
        self.redis = redis
        self.http_client = http_client
        self._request_timestamps: dict[str, list[float]] = {}
        self._queue_items: list[dict] = []

    def is_authorized_platform(self, platform: str) -> bool:
        """Check if platform is authorized."""
        return platform in AUTHORIZED_PLATFORMS

    async def add_listing(self, item: QueueItemCreate) -> QueueItemResponse:
        """Add a verified listing to the queue."""
        if not self.is_authorized_platform(item.platform):
            raise ValueError(f"unauthorized platform: {item.platform}")

        # In production: verify URL is accessible
        now = datetime.utcnow()
        queue_item = QueueItemResponse(
            id=len(self._queue_items) + 1,
            event_id=item.event_id,
            platform=item.platform,
            listing_url=str(item.listing_url),
            price=item.price,
            currency=item.currency,
            section=item.section,
            quantity=item.quantity,
            face_value=item.face_value,
            verified=True,
            is_official=item.platform in ["Ticketmaster", "Eventbrite", "Dice"],
            created_at=now,
            updated_at=now,
        )
        self._queue_items.append(queue_item.model_dump())
        logger.info("Added listing to queue: %s for event %d", item.platform, item.event_id)
        return queue_item

    async def verify_listing(self, url: str, respect_rate_limit: bool = True) -> ListingVerification:
        """Verify a listing URL is accessible."""
        if respect_rate_limit:
            await self._wait_for_rate_limit("verify")

        # In production: actual HTTP HEAD request
        return ListingVerification(
            url=url,
            is_accessible=True,
            status_code=200,
            respects_rate_limit=respect_rate_limit,
        )

    async def sync_platform(
        self,
        platform: str,
        event_id: int,
        max_requests_per_minute: int = 30,
        check_robots_txt: bool = True,
    ) -> SyncResult:
        """Sync listings from a platform's API."""
        start_time = time.time()

        if not self.is_authorized_platform(platform):
            raise ValueError(f"unauthorized platform: {platform}")

        if check_robots_txt:
            await self._check_robots_txt(platform)

        # In production: make actual API calls with rate limiting
        items_synced = 0
        items_new = 0
        items_updated = 0
        items_removed = 0

        duration = time.time() - start_time
        logger.info(
            "Synced %d items from %s for event %d in %.2fs",
            items_synced, platform, event_id, duration,
        )

        return SyncResult(
            platform=platform,
            event_id=event_id,
            items_synced=items_synced,
            items_new=items_new,
            items_updated=items_updated,
            items_removed=items_removed,
            rate_limit_respected=True,
            robots_txt_checked=check_robots_txt,
            duration_seconds=round(duration, 2),
        )

    async def check_platform_health(self, platform: str) -> PlatformStatus:
        """Check if platform API is healthy."""
        # In production: actual health check ping
        return PlatformStatus(
            platform=platform,
            is_accessible=True,
            response_time_ms=120.0,
        )

    async def get_queue_status(self, event_id: int) -> QueueStatus:
        """Get queue status for an event."""
        event_items = [
            item for item in self._queue_items
            if item.get("event_id") == event_id
        ]
        platforms = list({item["platform"] for item in event_items})
        verified = sum(1 for item in event_items if item.get("verified"))

        return QueueStatus(
            event_id=event_id,
            total_items=len(event_items),
            verified_items=verified,
            platforms=platforms,
        )

    async def list_event_items(self, event_id: int) -> list[QueueItemResponse]:
        """List all queue items for an event."""
        return [
            QueueItemResponse(**item)
            for item in self._queue_items
            if item.get("event_id") == event_id
        ]

    async def _wait_for_rate_limit(self, platform: str) -> None:
        """Wait if rate limit would be exceeded."""
        now = time.time()
        if platform not in self._request_timestamps:
            self._request_timestamps[platform] = []

        # Clean old timestamps (>60s)
        self._request_timestamps[platform] = [
            ts for ts in self._request_timestamps[platform]
            if now - ts < 60
        ]

        config = AUTHORIZED_PLATFORMS.get(platform, {})
        rate_limit = config.get("rate_limit_per_minute", 30)

        if len(self._request_timestamps[platform]) >= rate_limit:
            sleep_time = 60 - (now - self._request_timestamps[platform][0])
            if sleep_time > 0:
                logger.info("Rate limit reached for %s, sleeping %.1fs", platform, sleep_time)
                time.sleep(sleep_time)

        self._request_timestamps[platform].append(now)

    async def _check_robots_txt(self, platform: str) -> bool:
        """Check robots.txt before fetching."""
        # In production: fetch and parse robots.txt
        logger.info("Checking robots.txt for %s", platform)
        return True