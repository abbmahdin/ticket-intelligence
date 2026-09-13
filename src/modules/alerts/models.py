"""
SQLAlchemy models for the alerts module.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped

from src.database import Base


class AlertRule(Base):
    """A user-configured rule that triggers notifications."""

    __tablename__ = "alert_rules"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_email: Mapped[str] = Column(String(255), nullable=False, index=True)
    event_id: Mapped[int] = Column(Integer, nullable=False, index=True)
    artist_id: Mapped[int | None] = Column(Integer, nullable=True, index=True)
    venue_id: Mapped[int | None] = Column(Integer, nullable=True, index=True)
    alert_type: Mapped[str] = Column(String(50), nullable=False)
    threshold_price: Mapped[float | None] = Column(Numeric(10, 2), nullable=True)
    threshold_score: Mapped[float | None] = Column(Numeric(5, 4), nullable=True)
    notification_channel: Mapped[str] = Column(String(20), default="email")
    is_active: Mapped[bool] = Column(Boolean, default=True)
    is_triggered: Mapped[bool] = Column(Boolean, default=False)
    triggered_at: Mapped[datetime | None] = Column(DateTime, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class NotificationLog(Base):
    """Log of dispatched notifications."""

    __tablename__ = "notification_logs"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    alert_rule_id: Mapped[int] = Column(
        Integer, ForeignKey("alert_rules.id"), nullable=False
    )
    channel: Mapped[str] = Column(String(20), nullable=False)
    recipient: Mapped[str] = Column(String(255), nullable=False)
    subject: Mapped[str] = Column(String(500), nullable=False)
    body: Mapped[str] = Column(Text, nullable=False)
    status: Mapped[str] = Column(String(20), default="pending")
    sent_at: Mapped[datetime | None] = Column(DateTime, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)