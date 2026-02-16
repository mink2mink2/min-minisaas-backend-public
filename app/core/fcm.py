"""Firebase Cloud Messaging 초기화"""
import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging
from app.core.config import settings
import logging
import os

logger = logging.getLogger(__name__)

# Firebase Admin SDK 초기화
_firebase_app = None


def initialize_firebase():
    """Firebase Admin SDK 초기화"""
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    try:
        # Service Account Key 파일 경로
        cred_path = settings.FCM_CREDENTIALS_PATH

        # 절대 경로로 변환
        if not os.path.isabs(cred_path):
            # 상대 경로인 경우 백엔드 루트 기준으로 변환
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            cred_path = os.path.join(base_dir, cred_path)

        logger.info(f"Firebase initializing with credentials: {cred_path}")

        # Credentials 로드
        cred = credentials.Certificate(cred_path)

        # Firebase Admin SDK 초기화
        _firebase_app = firebase_admin.initialize_app(cred)

        logger.info("Firebase Admin SDK initialized successfully")
        return _firebase_app

    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        raise


def get_firebase_app():
    """Firebase App 인스턴스 반환"""
    if _firebase_app is None:
        initialize_firebase()
    return _firebase_app


def get_fcm_client():
    """FCM 메시징 클라이언트 반환"""
    app = get_firebase_app()
    return messaging.client(app)
