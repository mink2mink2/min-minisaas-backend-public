"""알림 서비스 - 다양한 채널(Slack, Email 등)로 알림 전송"""
from typing import Dict, Any
from app.core.config import settings
from app.core.notifications.slack import SlackNotifier
from app.core.events import SecurityAlertEvent

class NotificationService:
    """알림 통합 관리 서비스"""

    def __init__(self):
        self.slack_notifier = SlackNotifier()

    async def handle_security_alert(self, event: SecurityAlertEvent):
        """보안 경고 이벤트 처리 핸들러"""
        payload = event.payload
        severity = payload.get("severity", "LOW")
        
        # 1. Slack 알림 (설정되어 있는 경우)
        if settings.SLACK_WEBHOOK_URL:
            try:
                await self.slack_notifier.send_security_alert(
                    event_type=payload.get("event_type"),
                    user_id=payload.get("user_id"),
                    severity=severity,
                    details=payload.get("details", {})
                )
            except Exception as e:
                print(f"Failed to send Slack alert: {e}")

notification_service = NotificationService()
