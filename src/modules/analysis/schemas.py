"""
Pydantic schemas for the analysis module.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TrendDirection(str, Enum):
    """Price trend direction."""
    UPWARD = "upward"
    DOWNWARD = "downward"
    STABLE = "stable"
    INSUFFICIENT_DATA = "insufficient_data"


class HistoricalPriceQuery(BaseModel):
    """Query parameters for historical price data."""

    event_id: Optional[int] = None
    artist_id: Optional[int] = None
    venue_id: Optional[int] = None
    platform: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")


class PricePoint(BaseModel):
    """A single price data point."""

    model_config = ConfigDict(from_attributes=True)

    date: datetime
    price: float
    platform: Optional[str] = None
    currency: str = "EUR"


class PriceStatistics(BaseModel):
    """Statistical summary of price data."""

    min_price: Optional[float] = None
    max_price: Optional[float] = None
    avg_price: Optional[float] = None
    median_price: Optional[float] = None
    std_deviation: Optional[float] = None
    count: int = 0


class PriceTrend(BaseModel):
    """Price trend analysis result."""

    direction: TrendDirection
    slope: float
    change_percent: float
    data_points: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class MarketSummary(BaseModel):
    """Market summary for an event."""

    event_id: int
    event_title: Optional[str] = None
    current_lowest_price: Optional[float] = None
    current_highest_price: Optional[float] = None
    average_price: Optional[float] = None
    total_listings: int = 0
    trend_direction: TrendDirection = TrendDirection.INSUFFICIENT_DATA
    last_updated: datetime = Field(default_factory=datetime.utcnow)