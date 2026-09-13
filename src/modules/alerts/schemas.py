"""
Pydantic schemas for the alerts module.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AlertType(str, Enum):
    """Supported alert types."""
    PRICE_DROP = "price_drop"
    DEMAND_SPIKE = "demand_spike"
    BACK_IN_STOCK = "back_in_stock"


class NotificationChannel(str, Enum):
    """Supported notification channels."""
    EMAIL = "email"
    WEBHOOK = "webhook"


class AlertRuleCreate(BaseModel):
    """Schema for creating an alert rule."""

    user_email: EmailStr
    event_id: int
    alert_type: AlertType
    threshold_price: Optional[float] = Field(None, ge=0)
    threshold_score: Optional[float] = Field(None, ge=0, le=1)
    notification_channel: NotificationChannel = NotificationChannel.EMAIL


class AlertRuleUpdate(BaseModel):
    """Schema for updating an alert rule."""

    threshold_price: Optional[float] = Field(None, ge=0)
    threshold_score: Optional[float] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    """Schema for alert rule response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_email: str
    event_id: int
    alert_type: str
    threshold_price: Optional[float] = None
    threshold_score: Optional[float] = None
    notification_channel: str
    is_active: bool
    is_triggered: bool
    triggered_at: Optional[datetime] = None
    created_at: datetime


class AlertTriggerResult(BaseModel):
    """Result of evaluating an alert rule."""

    triggered: bool
    alert_id: int
    message: str = ""
    reason: str = ""


class NotificationLogResponse(BaseModel):
    """Schema for notification log response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_rule_id: int
    channel: str
    recipient: str
    subject: str
    body: str
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime


class AlertEvent(BaseModel):
    """Event data passed to alert evaluation."""

    event_id: int
    current_price: Optional[float] = None
    demand_score: Optional[float] = None
    in_stock: Optional[bool] = None
    platform: Optional[str] = None