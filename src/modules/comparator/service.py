"""
Comparator service — compares ticket prices across authorized platforms.
"""
import logging
import statistics
from datetime import datetime

from src.modules.comparator.schemas import (
    ComparisonRequest,
    ComparisonResult,
    PlatformPrice,
    PriceAnomaly,
    RankedPrices,
)

logger = logging.getLogger(__name__)

# Authorized resale platforms (verified legitimate)
AUTHORIZED_PLATFORMS = {
    "Ticketmaster": {"trust_score": 95, "is_authorized": True},
    "StubHub": {"trust_score": 85, "is_authorized": True},
    "Viagogo": {"trust_score": 70, "is_authorized": True},
    "SeatGeek": {"trust_score": 88, "is_authorized": True},
    "Eventbrite": {"trust_score": 90, "is_authorized": True},
    "Dice": {"trust_score": 92, "is_authorized": True},
}


class ComparatorService:
    """Service for comparing ticket prices across authorized platforms."""

    def __init__(self, redis=None):
        self.redis = redis

    def is_authorized_platform(self, platform: str) -> bool:
        """Check if a platform is an authorized reseller."""
        return AUTHORIZED_PLATFORMS.get(platform, {}).get("is_authorized", False)

    async def compare(self, request: ComparisonRequest) -> ComparisonResult:
        """
        Compare prices across authorized platforms for an event.

        In production: queries each platform's API for current listings.
        """
        # In production: fetch from platform APIs
        # For now, return empty result
        platform_prices: list[PlatformPrice] = []

        ranked = await self._rank_prices(platform_prices)
        anomalies = await self.detect_anomalies(
            [p.price for p in platform_prices]
        ) if platform_prices else []

        warnings = []
        for price in platform_prices:
            if not self.is_authorized_platform(price.platform):
                warnings.append(
                    f"Platform '{price.platform}' is not an authorized reseller."
                )

        return ComparisonResult(
            event_id=request.event_id,
            platform_prices=platform_prices,
            ranked_prices=ranked.ranked_prices,
            lowest_price=ranked.lowest_price,
            highest_price=ranked.highest_price,
            average_price=ranked.average_price,
            anomalies=anomalies,
            warnings=warnings,
        )

    async def _rank_prices(
        self, prices: list[PlatformPrice]
    ) -> RankedPrices:
        """Rank prices from lowest to highest."""
        if not prices:
            return RankedPrices(
                ranked_prices=[],
                lowest_price=None,
                highest_price=None,
                average_price=None,
            )

        sorted_prices = sorted(prices, key=lambda p: p.price)
        price_values = [p.price for p in sorted_prices]

        return RankedPrices(
            ranked_prices=sorted_prices,
            lowest_price=min(price_values),
            highest_price=max(price_values),
            average_price=round(statistics.mean(price_values), 2),
        )

    async def detect_anomalies(
        self, prices: list[float], threshold_std: float = 2.0
    ) -> list[PriceAnomaly]:
        """
        Detect anomalous prices using the modified z-score (median + MAD).

        A single extreme outlier inflates a plain mean/stdev enough to mask
        itself, so deviations are measured against the median and the
        median absolute deviation instead. Prices whose modified z-score
        exceeds `threshold_std` are flagged as anomalous.
        """
        if len(prices) < 3:
            return []

        mean = statistics.mean(prices)
        median_price = statistics.median(prices)
        mad = statistics.median(abs(price - median_price) for price in prices)

        if mad == 0:
            return []

        anomalies = []
        for i, price in enumerate(prices):
            z_score = abs(0.6745 * (price - median_price) / mad)
            if z_score > threshold_std:
                anomalies.append(
                    PriceAnomaly(
                        platform=f"platform_{i}",
                        price=price,
                        deviation=round(z_score, 2),
                        market_average=round(mean, 2),
                        message=(
                            f"Price {price} deviates {z_score:.1f} standard "
                            f"deviations from market average {mean:.2f}"
                        ),
                    )
                )

        return anomalies