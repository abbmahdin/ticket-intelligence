"""
Alert service — evaluates alert rules and determines whether to trigger.
"""
import logging
from datetime import datetime
from typing import Any

from src.modules.alerts.models import AlertRule, NotificationLog
from src.modules.alerts.schemas import AlertTriggerResult

logger = logging.getLogger(__name__)


class AlertService:
    """Service for evaluating alert rules and triggering notifications."""

    def __init__(
        self,
        redis=None,
        task_dispatcher=None,
    ):
        self.redis = redis
        self.task_dispatcher = task_dispatcher

    async def evaluate(
        self,
        rule: AlertRule,
        current_price: float | None = None,
        demand_score: float | None = None,
        in_stock: bool | None = None,
    ) -> AlertTriggerResult:
        """
        Evaluate whether an alert rule should trigger.

        Rules:
        - alert must be active
        - alert must not have already triggered (unless reset)
        - price_drop: triggers when current_price <= threshold_price
        - demand_spike: triggers when demand_score >= threshold_score
        - back_in_stock: triggers when in_stock becomes True
        """
        if not rule.is_active:
            return AlertTriggerResult(
                triggered=False,
                alert_id=rule.id,
                reason="alert_inactive",
            )

        if rule.is_triggered:
            return AlertTriggerResult(
                triggered=False,
                alert_id=rule.id,
                reason="already_triggered",
            )

        if rule.alert_type == "price_drop":
            return self._evaluate_price_drop(rule, current_price)
        elif rule.alert_type == "demand_spike":
            return self._evaluate_demand_spike(rule, demand_score)
        elif rule.alert_type == "back_in_stock":
            return self._evaluate_back_in_stock(rule, in_stock)
        else:
            logger.warning("Unknown alert type: %s", rule.alert_type)
            return AlertTriggerResult(
                triggered=False,
                alert_id=rule.id,
                reason=f"unknown_alert_type:{rule.alert_type}",
            )

    def _evaluate_price_drop(
        self, rule: AlertRule, current_price: float | None
    ) -> AlertTriggerResult:
        """Price drop triggers when current price is at or below threshold."""
        if current_price is None or rule.threshold_price is None:
            return AlertTriggerResult(
                triggered=False,
                alert_id=rule.id,
                reason="missing_price_data",
            )

        if current_price <= rule.threshold_price:
            return AlertTriggerResult(
                triggered=True,
                alert_id=rule.id,
                message=f"Price dropped to {current_price} (threshold: {rule.threshold_price})",
            )
        return AlertTriggerResult(
            triggered=False,
            alert_id=rule.id,
            reason="price_above_threshold",
        )

    def _evaluate_demand_spike(
        self, rule: AlertRule, demand_score: float | None
    ) -> AlertTriggerResult:
        """Demand spike triggers when score exceeds threshold."""
        if demand_score is None or rule.threshold_score is None:
            return AlertTriggerResult(
                triggered=False,
                alert_id=rule.id,
                reason="missing_demand_data",
            )

        if demand_score >= rule.threshold_score:
            return AlertTriggerResult(
                triggered=True,
                alert_id=rule.id,
                message=f"Demand spike detected: score {demand_score} (threshold: {rule.threshold_score})",
            )
        return AlertTriggerResult(
            triggered=False,
            alert_id=rule.id,
            reason="demand_below_threshold",
        )

    def _evaluate_back_in_stock(
        self, rule: AlertRule, in_stock: bool | None
    ) -> AlertTriggerResult:
        """Back-in-stock triggers when stock becomes available."""
        if in_stock is True:
            return AlertTriggerResult(
                triggered=True,
                alert_id=rule.id,
                message="Tickets are back in stock!",
            )
        return AlertTriggerResult(
            triggered=False,
            alert_id=rule.id,
            reason="out_of_stock",
        )

    async def mark_triggered(self, alert_id: int) -> None:
        """Mark an alert as triggered with timestamp."""
        # In real impl: update DB record
        logger.info("Alert %d marked as triggered at %s", alert_id, datetime.utcnow().isoformat())

    async def list_user_alerts(self, user_email: str) -> list[dict[str, Any]]:
        """Return all alerts configured by a user."""
        # In real impl: query DB
        return []

    async def deactivate_alert(self, alert_id: int, user_email: str) -> bool:
        """Deactivate an alert rule."""
        logger.info("Deactivating alert %d for %s", alert_id, user_email)
        return True

    async def delete_alert(self, alert_id: int, user_email: str) -> bool:
        """Delete an alert rule."""
        logger.info("Deleting alert %d for %s", alert_id, user_email)
        return True