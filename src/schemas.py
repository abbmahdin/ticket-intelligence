"""
Shared Pydantic schemas for Ticket Intelligence API.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── Artist ──────────────────────────────────────────────────────────────────

class ArtistBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    genre: Optional[str] = None
    popularity_score: Optional[float] = Field(None, ge=0, le=100)


class ArtistCreate(ArtistBase):
    external_id: Optional[str] = None


class ArtistResponse(ArtistBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: Optional[str] = None
    created_at: datetime


# ── Venue ───────────────────────────────────────────────────────────────────

class VenueBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=150)
    country: str = Field(..., min_length=1, max_length=100)
    capacity: Optional[int] = Field(None, ge=0)


class VenueCreate(VenueBase):
    external_id: Optional[str] = None


class VenueResponse(VenueBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: Optional[str] = None
    created_at: datetime


# ── Event ───────────────────────────────────────────────────────────────────

class EventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    artist_id: int
    venue_id: int
    event_date: datetime
    demand_score: Optional[float] = Field(None, ge=0, le=1)


class EventCreate(EventBase):
    external_id: Optional[str] = None


class EventResponse(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Price Record ────────────────────────────────────────────────────────────

class PriceRecordBase(BaseModel):
    event_id: int
    platform: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., ge=0)
    currency: str = Field(default="EUR", max_length=3)


class PriceRecordCreate(PriceRecordBase):
    pass


class PriceRecordResponse(PriceRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recorded_at: datetime


# ── Alert ───────────────────────────────────────────────────────────────────

class AlertBase(BaseModel):
    user_email: EmailStr
    alert_type: str = Field(..., pattern="^(price_drop|demand_spike|back_in_stock)$")
    threshold_value: Optional[float] = Field(None, ge=0)


class AlertCreate(AlertBase):
    event_id: Optional[int] = None
    artist_id: Optional[int] = None
    venue_id: Optional[int] = None


class AlertResponse(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: Optional[int] = None
    artist_id: Optional[int] = None
    venue_id: Optional[int] = None
    is_triggered: bool
    is_active: bool
    created_at: datetime


# ── Legal Queue ─────────────────────────────────────────────────────────────

class LegalQueueItemBase(BaseModel):
    event_id: int
    platform: str = Field(..., min_length=1, max_length=100)
    listing_url: str = Field(..., min_length=1)
    price: float = Field(..., ge=0)
    currency: str = Field(default="EUR", max_length=3)


class LegalQueueItemCreate(LegalQueueItemBase):
    pass


class LegalQueueItemResponse(LegalQueueItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    verified: bool
    created_at: datetime


# ── Prediction ──────────────────────────────────────────────────────────────

class PredictionRequest(BaseModel):
    artist_id: int
    venue_id: int
    event_date: datetime


class PredictionResponse(BaseModel):
    artist_id: int
    venue_id: int
    event_date: datetime
    demand_score: float = Field(..., ge=0, le=1)
    confidence: float = Field(..., ge=0, le=1)
    factors: dict


# ── Comparison ──────────────────────────────────────────────────────────────

class ComparisonRequest(BaseModel):
    event_id: int


class PlatformPrice(BaseModel):
    platform: str
    price: float
    currency: str
    listing_url: Optional[str] = None


class ComparisonResponse(BaseModel):
    event_id: int
    event_title: str
    prices: list[PlatformPrice]
    lowest_price: Optional[float] = None
    highest_price: Optional[float] = None
    average_price: Optional[float] = None