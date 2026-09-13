"""
Notification dispatcher — sends alerts via email, webhook, etc.
"""
import logging
from datetime import datetime
from typing import Any

from src.modules.alerts.models import NotificationLog

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Dispatches notifications through configured channels."""

    def __init__(self, task_dispatcher=None):
        self.task_dispatcher = task_dispatcher

    async def send(
        self,
        channel: str,
        recipient: str,
        subject: str,
        body: str,
        alert_rule_id: int | None = None,
    ) -> NotificationLog:
        """
        Send a notification through the specified channel.

        Channels:
        - email: dispatches via Celery task `send_email_notification`
        - webhook: dispatches via Celery task `send_webhook_notification`
        """
        log = NotificationLog(
            alert_rule_id=alert_rule_id or 0,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            status="dispatched",
        )

        if self.task_dispatcher:
            if channel == "email":
                self.task_dispatcher.send_task(
                    "send_email_notification",
                    args=[recipient, subject, body],
                )
            elif channel == "webhook":
                self.task_dispatcher.send_task(
                    "send_webhook_notification",
                    args=[recipient, subject, body],
                )
            else:
                log.status = "unsupported_channel"
                logger.warning("Unsupported notification channel: %s", channel)
                return log
        else:
            # No task dispatcher configured — log only
            log.status = "logged_only"
            logger.info(
                "[NOTIFICATION:%s] To: %s | Subject: %s",
                channel,
                recipient,
                subject,
            )

        log.sent_at = datetime.utcnow()
        return log

    async def send_batch(
        self,
        notifications: list[dict[str, Any]],
    ) -> list[NotificationLog]:
        """Send multiple notifications in batch."""
        logs = []
        for notif in notifications:
            log = await self.send(
                channel=notif["channel"],
                recipient=notif["recipient"],
                subject=notif["subject"],
                body=notif["body"],
                alert_rule_id=notif.get("alert_rule_id"),
            )
            logs.append(log)
        return logs