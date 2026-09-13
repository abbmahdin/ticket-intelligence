"""
Analysis service — computes statistics and trends from price data.
"""
import logging
import statistics
from datetime import datetime

from src.modules.analysis.schemas import (
    MarketSummary,
    PriceStatistics,
    PriceTrend,
    TrendDirection,
)

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service for analyzing historical ticket price data."""

    def __init__(self, redis=None):
        self.redis = redis

    async def compute_statistics(self, prices: list[float]) -> PriceStatistics:
        """Compute statistical summary of a list of prices."""
        if not prices:
            return PriceStatistics(count=0)

        sorted_prices = sorted(prices)
        n = len(sorted_prices)

        avg = sum(sorted_prices) / n
        median = statistics.median(sorted_prices)
        std = statistics.stdev(sorted_prices) if n > 1 else 0.0

        return PriceStatistics(
            min_price=sorted_prices[0],
            max_price=sorted_prices[-1],
            avg_price=round(avg, 2),
            median_price=median,
            std_deviation=round(std, 2),
            count=n,
        )

    async def detect_trend(
        self, price_points: list[dict]
    ) -> PriceTrend:
        """
        Detect price trend from chronological price points.

        Uses simple linear regression on the price series.
        """
        if len(price_points) < 2:
            return PriceTrend(
                direction=TrendDirection.INSUFFICIENT_DATA,
                slope=0.0,
                change_percent=0.0,
                data_points=len(price_points),
            )

        # Sort by date
        sorted_points = sorted(price_points, key=lambda p: p["date"])

        # Convert dates to numeric (days since first point)
        base_date = sorted_points[0]["date"]
        x_values = [(p["date"] - base_date).total_seconds() / 86400 for p in sorted_points]
        y_values = [p["price"] for p in sorted_points]

        n = len(x_values)
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n

        # Linear regression slope
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator

        # Calculate percentage change
        start_price = y_values[0]
        end_price = y_values[-1]
        if start_price > 0:
            change_percent = ((end_price - start_price) / start_price) * 100
        else:
            change_percent = 0.0

        # Determine direction with threshold
        slope_threshold = 0.5  # €/day
        if slope > slope_threshold:
            direction = TrendDirection.UPWARD
        elif slope < -slope_threshold:
            direction = TrendDirection.DOWNWARD
        else:
            direction = TrendDirection.STABLE

        return PriceTrend(
            direction=direction,
            slope=round(slope, 4),
            change_percent=round(change_percent, 2),
            data_points=n,
            start_date=sorted_points[0]["date"],
            end_date=sorted_points[-1]["date"],
        )

    async def get_market_summary(self, event_id: int) -> MarketSummary:
        """Generate a market summary for an event, with Redis caching."""
        cache_key = f"analysis:market_summary:{event_id}"

        # Try cache first
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                # In production, deserialize from JSON
                pass

        # In production: query DB for price data
        summary = MarketSummary(
            event_id=event_id,
            current_lowest_price=None,
            current_highest_price=None,
            average_price=None,
            total_listings=0,
            trend_direction=TrendDirection.INSUFFICIENT_DATA,
            last_updated=datetime.utcnow(),
        )

        # Cache for 5 minutes
        if self.redis:
            await self.redis.setex(
                cache_key,
                300,  # 5 min TTL
                summary.model_dump_json(),
            )

        return summary