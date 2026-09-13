"""
Tests for the alerts module.
TDD approach: tests written first, then implementation follows.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.modules.alerts.service import AlertService
from src.modules.alerts.models import AlertRule, NotificationLog
from src.modules.alerts.schemas import (
    AlertRuleCreate,
    AlertRuleResponse,
    AlertTriggerResult,
)


class TestAlertRuleCreation:
    """Tests for creating alert rules."""

    def test_create_price_drop_alert(self):
        """Should create a price drop alert with valid data."""
        rule = AlertRuleCreate(
            user_email="fan@example.com",
            event_id=1,
            alert_type="price_drop",
            threshold_price=70.00,
            notification_channel="email",
        )
        assert rule.alert_type == "price_drop"
        assert rule.threshold_price == 70.00
        assert rule.user_email == "fan@example.com"

    def test_create_demand_spike_alert(self):
        """Should create a demand spike alert."""
        rule = AlertRuleCreate(
            user_email="fan@example.com",
            event_id=1,
            alert_type="demand_spike",
            threshold_score=0.85,
            notification_channel="email",
        )
        assert rule.alert_type == "demand_spike"
        assert rule.threshold_score == 0.85

    def test_create_back_in_stock_alert(self):
        """Should create a back-in-stock alert without threshold."""
        rule = AlertRuleCreate(
            user_email="fan@example.com",
            event_id=1,
            alert_type="back_in_stock",
            notification_channel="email",
        )
        assert rule.alert_type == "back_in_stock"
        assert rule.threshold_price is None

    def test_invalid_alert_type_rejected(self):
        """Should reject invalid alert types."""
        with pytest.raises(ValueError):
            AlertRuleCreate(
                user_email="fan@example.com",
                event_id=1,
                alert_type="invalid_type",
                notification_channel="email",
            )

    def test_invalid_email_rejected(self):
        """Should reject invalid email format."""
        with pytest.raises(ValueError):
            AlertRuleCreate(
                user_email="not-an-email",
                event_id=1,
                alert_type="price_drop",
                notification_channel="email",
            )


class TestAlertTriggering:
    """Tests for triggering alerts based on conditions."""

    @pytest.fixture
    def alert_service(self, mock_redis, mock_celery_task):
        return AlertService(redis=mock_redis, task_dispatcher=mock_celery_task)

    @pytest.mark.asyncio
    async def test_trigger_price_drop_alert(self, alert_service):
        """Should trigger when current price drops below threshold."""
        rule = AlertRule(
            id=1,
            user_email="fan@example.com",
            event_id=1,
            alert_type="price_drop",
            threshold_price=70.00,
            notification_channel="email",
            is_active=True,
            is_triggered=False,
        )
        current_price = 65.00

        result = await alert_service.evaluate(rule, current_price=current_price)

        assert result.triggered is True
        assert result.alert_id == 1
        assert result.message == "Price dropped to 65.0 (threshold: 70.0)"

    @pytest.mark.asyncio
    async def test_no_trigger_when_price_above_threshold(self, alert_service):
        """Should NOT trigger when current price is above threshold."""
        rule = AlertRule(
            id=2,
            user_email="fan@example.com",
            event_id=1,
            alert_type="price_drop",
            threshold_price=70.00,
            notification_channel="email",
            is_active=True,
            is_triggered=False,
        )
        current_price = 80.00

        result = await alert_service.evaluate(rule, current_price=current_price)

        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_trigger_demand_spike(self, alert_service):
        """Should trigger when demand score exceeds threshold."""
        rule = AlertRule(
            id=3,
            user_email="fan@example.com",
            event_id=1,
            alert_type="demand_spike",
            threshold_score=0.85,
            notification_channel="email",
            is_active=True,
            is_triggered=False,
        )
        current_score = 0.92

        result = await alert_service.evaluate(rule, demand_score=current_score)

        assert result.triggered is True
        assert result.message == "Demand spike detected: score 0.92 (threshold: 0.85)"

    @pytest.mark.asyncio
    async def test_no_trigger_for_inactive_alert(self, alert_service):
        """Should NOT trigger inactive alerts."""
        rule = AlertRule(
            id=4,
            user_email="fan@example.com",
            event_id=1,
            alert_type="price_drop",
            threshold_price=70.00,
            notification_channel="email",
            is_active=False,
            is_triggered=False,
        )

        result = await alert_service.evaluate(rule, current_price=50.00)

        assert result.triggered is False
        assert result.reason == "alert_inactive"

    @pytest.mark.asyncio
    async def test_no_retrigger_already_triggered(self, alert_service):
        """Should NOT re-trigger alerts that have already fired."""
        rule = AlertRule(
            id=5,
            user_email="fan@example.com",
            event_id=1,
            alert_type="price_drop",
            threshold_price=70.00,
            notification_channel="email",
            is_active=True,
            is_triggered=True,
        )

        result = await alert_service.evaluate(rule, current_price=50.00)

        assert result.triggered is False
        assert result.reason == "already_triggered"


class TestNotificationDispatch:
    """Tests for dispatching notifications when alerts trigger."""

    @pytest.mark.asyncio
    async def test_dispatch_email_notification(self, mock_celery_task):
        """Should dispatch email notification via Celery."""
        from src.modules.alerts.notifications import NotificationDispatcher

        dispatcher = NotificationDispatcher(task_dispatcher=mock_celery_task)

        await dispatcher.send(
            channel="email",
            recipient="fan@example.com",
            subject="Price drop alert",
            body="Price dropped to €65!",
        )

        mock_celery_task.send_task.assert_called_once_with(
            "send_email_notification",
            args=["fan@example.com", "Price drop alert", "Price dropped to €65!"],
        )

    @pytest.mark.asyncio
    async def test_dispatch_webhook_notification(self, mock_celery_task):
        """Should dispatch webhook notification."""
        from src.modules.alerts.notifications import NotificationDispatcher

        dispatcher = NotificationDispatcher(task_dispatcher=mock_celery_task)

        await dispatcher.send(
            channel="webhook",
            recipient="https://hooks.example.com/ticket-alert",
            subject="Alert",
            body="Test body",
        )

        mock_celery_task.send_task.assert_called_once_with(
            "send_webhook_notification",
            args=["https://hooks.example.com/ticket-alert", "Alert", "Test body"],
        )

    @pytest.mark.asyncio
    async def test_log_notification(self, mock_celery_task):
        """Should log notification after dispatch."""
        from src.modules.alerts.notifications import NotificationDispatcher

        dispatcher = NotificationDispatcher(task_dispatcher=mock_celery_task)

        log = await dispatcher.send(
            channel="email",
            recipient="fan@example.com",
            subject="Alert",
            body="Body",
        )

        assert log.channel == "email"
        assert log.recipient == "fan@example.com"
        assert log.status == "dispatched"


class TestAlertListing:
    """Tests for listing and managing user alerts."""

    @pytest.mark.asyncio
    async def test_list_user_alerts(self, mock_redis):
        """Should return all active alerts for a user."""
        service = AlertService(redis=mock_redis)

        alerts = await service.list_user_alerts("fan@example.com")

        assert isinstance(alerts, list)

    @pytest.mark.asyncio
    async def test_deactivate_alert(self, mock_redis):
        """Should deactivate an alert by ID."""
        service = AlertService(redis=mock_redis)

        result = await service.deactivate_alert(alert_id=1, user_email="fan@example.com")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_alert(self, mock_redis):
        """Should delete an alert by ID."""
        service = AlertService(redis=mock_redis)

        result = await service.delete_alert(alert_id=1, user_email="fan@example.com")

        assert result is True