"""
Shared SQLAlchemy models for Ticket Intelligence.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text, Boolean
from sqlalchemy.orm import Mapped

from src.database import Base


class Artist(Base):
    """An artist/band with demand scoring metadata."""

    __tablename__ = "artists"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(255), nullable=False, index=True)
    external_id: Mapped[str | None] = Column(String(100), unique=True, nullable=True)
    genre: Mapped[str | None] = Column(String(100), nullable=True)
    popularity_score: Mapped[float | None] = Column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)


class Venue(Base):
    """A concert venue."""

    __tablename__ = "venues"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String(255), nullable=False)
    city: Mapped[str] = Column(String(150), nullable=False)
    country: Mapped[str] = Column(String(100), nullable=False)
    capacity: Mapped[int | None] = Column(Integer, nullable=True)
    external_id: Mapped[str | None] = Column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    """A concert event tying artist, venue, and date together."""

    __tablename__ = "events"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    title: Mapped[str] = Column(String(500), nullable=False)
    artist_id: Mapped[int] = Column(Integer, nullable=False, index=True)
    venue_id: Mapped[int] = Column(Integer, nullable=False, index=True)
    event_date: Mapped[datetime] = Column(DateTime, nullable=False, index=True)
    demand_score: Mapped[float | None] = Column(Numeric(5, 4), nullable=True)
    external_id: Mapped[str | None] = Column(String(100), unique=True, nullable=True)
    is_active: Mapped[bool] = Column(Boolean, default=True)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PriceRecord(Base):
    """Historical price record for a ticket from a platform."""

    __tablename__ = "price_records"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = Column(Integer, nullable=False, index=True)
    platform: Mapped[str] = Column(String(100), nullable=False)
    price: Mapped[float] = Column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = Column(String(3), default="EUR")
    recorded_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, index=True)


class Alert(Base):
    """User-configured price or demand alert."""

    __tablename__ = "alerts"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_email: Mapped[str] = Column(String(255), nullable=False, index=True)
    event_id: Mapped[int | None] = Column(Integer, nullable=True)
    artist_id: Mapped[int | None] = Column(Integer, nullable=True)
    venue_id: Mapped[int | None] = Column(Integer, nullable=True)
    alert_type: Mapped[str] = Column(String(50), nullable=False)
    threshold_value: Mapped[float | None] = Column(Numeric(10, 2), nullable=True)
    is_triggered: Mapped[bool] = Column(Boolean, default=False)
    is_active: Mapped[bool] = Column(Boolean, default=True)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)


class LegalQueueItem(Base):
    """Tracks a ticket found on an authorized reseller platform."""

    __tablename__ = "legal_queue_items"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = Column(Integer, nullable=False, index=True)
    platform: Mapped[str] = Column(String(100), nullable=False)
    listing_url: Mapped[str] = Column(Text, nullable=False)
    price: Mapped[float] = Column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = Column(String(3), default="EUR")
    verified: Mapped[bool] = Column(Boolean, default=False)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)