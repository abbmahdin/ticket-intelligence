"""
Pydantic schemas for the comparator module.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ComparisonRequest(BaseModel):
    """Request to compare prices across platforms."""

    event_id: int
    section: Optional[str] = None
    quantity: int = Field(default=1, ge=1, le=20)


class PlatformPrice(BaseModel):
    """Price listing on a specific platform."""

    platform: str
    price: float
    currency: str = "EUR"
    listing_url: Optional[str] = None
    section: Optional[str] = None
    is_verified: bool = False


class PriceAnomaly(BaseModel):
    """An anomalous price detection result."""

    platform: str
    price: float
    deviation: float  # z-score deviation from mean
    market_average: float
    message: str


class RankedPrices(BaseModel):
    """Prices ranked from lowest to highest."""

    ranked_prices: list[PlatformPrice]
    lowest_price: Optional[float] = None
    highest_price: Optional[float] = None
    average_price: Optional[float] = None


class ComparisonResult(BaseModel):
    """Full comparison result for an event."""

    event_id: int
    event_title: Optional[str] = None
    platform_prices: list[PlatformPrice]
    ranked_prices: list[PlatformPrice] = []
    lowest_price: Optional[float] = None
    highest_price: Optional[float] = None
    average_price: Optional[float] = None
    anomalies: list[PriceAnomaly] = []
    warnings: list[str] = []
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class PlatformRating(BaseModel):
    """Rating/trust score for a resale platform."""

    platform: str
    is_authorized: bool
    trust_score: float = Field(..., ge=0, le=100)
    notes: str = ""