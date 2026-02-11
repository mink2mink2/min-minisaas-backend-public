"""이벤트 기반 보안 알림 테스트"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.events import SecurityAlertEvent, event_bus
from app.core.notifications.notification_service import notification_service
from app.core.auth import jwt_manager
from app.core.config import settings

@pytest.mark.asyncio
async def test_security_alert_event_emitted_on_token_reuse(mock_cache, monkeypatch):
    """토큰 재사용 감지 시 SecurityAlertEvent가 발행되는지 테스트"""
    # 1. EventBus.emit을 스파이로 설정
    spy_emit = AsyncMock(side_effect=event_bus.emit)
    monkeypatch.setattr(event_bus, "emit", spy_emit)
    
    # 2. AsyncSessionLocal mock (DB 저장 방지)
    mock_db = AsyncMock()
    mock_session_local = MagicMock(return_value=mock_db)
    monkeypatch.setattr("app.core.database.AsyncSessionLocal", mock_session_local)
    
    user_id = "test-user"
    device_id = "test-device"
    token = "stolen-token"
    
    # 첫 번째 사용 (정상)
    await jwt_manager.detect_and_log_refresh_reuse(user_id, device_id, token, 30)
    
    # 두 번째 사용 (재사용 감지)
    await jwt_manager.detect_and_log_refresh_reuse(user_id, device_id, token, 30)
    
    # 3. 이벤트 발행 확인
    # 첫 번째는 발행 안 됨(정상이니까), 두 번째에서 발행되어야 함
    # 하지만 _log_security_event는 재사용 감지 시에만 호출됨
    
    # SecurityAlertEvent가 인자로 전달되었는지 확인
    emitted_events = [args[0] for args, kwargs in spy_emit.call_args_list]
    security_events = [e for e in emitted_events if isinstance(e, SecurityAlertEvent)]
    
    assert len(security_events) == 1
    assert security_events[0].payload["event_type"] == "TOKEN_REUSE_DETECTED"
    assert security_events[0].payload["user_id"] == user_id
    assert security_events[0].payload["severity"] == "HIGH"

@pytest.mark.asyncio
async def test_notification_service_calls_slack(monkeypatch):
    """NotificationService가 이벤트를 받았을 때 Slack 알림을 보내는지 테스트"""
    # 1. SlackNotifier.send_security_alert mock
    mock_send = AsyncMock()
    # NotificationService 인스턴스가 내부적으로 사용하는 slack_notifier를 모킹
    monkeypatch.setattr(notification_service.slack_notifier, "send_security_alert", mock_send)
    
    # 2. SLACK_WEBHOOK_URL 설정 강제 (테스트 환경에서 None일 수 있음)
    monkeypatch.setattr(settings, "SLACK_WEBHOOK_URL", "https://fake-webhook.com")
    
    event = SecurityAlertEvent(
        user_id="user-1",
        event_type="TEST_EVENT",
        severity="MEDIUM",
        details={"info": "test"}
    )
    
    # 3. 핸들러 직접 호출
    await notification_service.handle_security_alert(event)
    
    # 4. Slack 호출 확인
    mock_send.assert_called_once_with(
        event_type="TEST_EVENT",
        user_id="user-1",
        severity="MEDIUM",
        details={"info": "test"}
    )
