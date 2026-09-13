"""
Pydantic schemas for the legal-queue module.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class PlatformName(str, Enum):
    """Authorized resale platforms."""
    TICKETMASTER = "Ticketmaster"
    STUBHUB = "StubHub"
    VIAGOGO = "Viagogo"
    SEATGEK = "SeatGeek"
    EVENTBRITE = "Eventbrite"
    DICE = "Dice"


class QueueItemCreate(BaseModel):
    """Schema for adding a listing to the legal queue."""

    event_id: int
    platform: str = Field(..., min_length=1, max_length=100)
    listing_url: HttpUrl
    price: float = Field(..., ge=0)
    currency: str = Field(default="EUR", max_length=3)
    section: Optional[str] = None
    quantity: int = Field(default=1, ge=1, le=20)
    face_value: Optional[float] = Field(None, ge=0)


class QueueItemResponse(BaseModel):
    """Schema for queue item response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    platform: str
    listing_url: str
    price: float
    currency: str
    section: Optional[str] = None
    quantity: int
    face_value: Optional[float] = None
    verified: bool
    is_official: bool
    created_at: datetime
    updated_at: datetime


class SellerListing(BaseModel):
    """A ticket listing from an authorized seller."""

    platform: str
    event_id: int
    listing_url: str
    price: float
    currency: str = "EUR"
    face_value: Optional[float] = None
    is_official: bool = False
    section: Optional[str] = None
    quantity: int = 1

    @property
    def premium_percent(self) -> Optional[float]:
        """Calculate premium percentage over face value."""
        if self.face_value and self.face_value > 0:
            return round(((self.price - self.face_value) / self.face_value) * 100, 2)
        return None


class PlatformStatus(BaseModel):
    """Health status of a platform API."""

    platform: str
    is_accessible: bool
    response_time_ms: Optional[float] = None
    last_checked: datetime = Field(default_factory=datetime.utcnow)
    rate_limit_remaining: Optional[int] = None


class SyncResult(BaseModel):
    """Result of syncing listings from a platform."""

    platform: str
    event_id: int
    items_synced: int
    items_new: int
    items_updated: int
    items_removed: int
    rate_limit_respected: bool = True
    robots_txt_checked: bool = True
    duration_seconds: float
    synced_at: datetime = Field(default_factory=datetime.utcnow)


class ListingVerification(BaseModel):
    """Result of verifying a listing URL is accessible."""

    url: str
    is_accessible: bool
    status_code: int
    respects_rate_limit: bool = True
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class QueueStatus(BaseModel):
    """Status of the legal queue for an event."""

    event_id: int
    total_items: int
    verified_items: int
    platforms: list[str]
    last_sync: Optional[datetime] = None