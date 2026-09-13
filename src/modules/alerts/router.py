"""
FastAPI router for the alerts module.
"""
from fastapi import APIRouter, HTTPException, status

from src.modules.alerts.schemas import (
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])

# In-memory store for demo (replace with DB in production)
_alert_rules: dict[int, dict] = {}
_next_id = 1


@router.post("/", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(rule: AlertRuleCreate):
    """Create a new alert rule."""
    global _next_id
    alert = {
        "id": _next_id,
        "user_email": rule.user_email,
        "event_id": rule.event_id,
        "artist_id": None,
        "venue_id": None,
        "alert_type": rule.alert_type.value,
        "threshold_price": rule.threshold_price,
        "threshold_score": rule.threshold_score,
        "notification_channel": rule.notification_channel.value,
        "is_active": True,
        "is_triggered": False,
        "triggered_at": None,
        "created_at": __import__("datetime").datetime.utcnow(),
        "updated_at": __import__("datetime").datetime.utcnow(),
    }
    _alert_rules[_next_id] = alert
    _next_id += 1
    return alert


@router.get("/", response_model=list[AlertRuleResponse])
async def list_alerts(user_email: str | None = None):
    """List alert rules, optionally filtered by user email."""
    alerts = list(_alert_rules.values())
    if user_email:
        alerts = [a for a in alerts if a["user_email"] == user_email]
    return alerts


@router.get("/{alert_id}", response_model=AlertRuleResponse)
async def get_alert(alert_id: int):
    """Get a specific alert rule by ID."""
    if alert_id not in _alert_rules:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _alert_rules[alert_id]


@router.patch("/{alert_id}", response_model=AlertRuleResponse)
async def update_alert(alert_id: int, update: AlertRuleUpdate):
    """Update an alert rule."""
    if alert_id not in _alert_rules:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert = _alert_rules[alert_id]
    if update.threshold_price is not None:
        alert["threshold_price"] = update.threshold_price
    if update.threshold_score is not None:
        alert["threshold_score"] = update.threshold_score
    if update.is_active is not None:
        alert["is_active"] = update.is_active
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(alert_id: int):
    """Delete an alert rule."""
    if alert_id not in _alert_rules:
        raise HTTPException(status_code=404, detail="Alert not found")
    del _alert_rules[alert_id]
    return None