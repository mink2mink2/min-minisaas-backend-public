"""Push models"""
from app.domain.push.models.fcm_token import FcmToken  # noqa: F401
from app.domain.push.models.push_notification import PushNotification  # noqa: F401

__all__ = [
    "FcmToken",
    "PushNotification",
]
