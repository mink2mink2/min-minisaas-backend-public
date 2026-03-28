"""푸시 알림 API 엔드포인트"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.core.database import get_db
from app.core.rate_limit import enforce_user_rate_limit
from app.api.v1.dependencies.api_key import verify_api_key
from app.api.v1.dependencies.auth import verify_any_platform, AuthResult
from app.domain.push.models.fcm_token import FcmToken
from app.domain.push.models.push_notification import PushNotification
from app.domain.push.services.push_service import PushService
from app.domain.push.schemas import (
    FcmTokenRegister, FcmTokenUpdate, FcmTokenResponse,
    PushNotificationResponse, UnreadCountResponse, MarkAllAsReadResponse
)
from app.schemas.response import PaginatedResponse

router = APIRouter(prefix="/push", tags=["push"])


# ============================================================================
# FCM Token 관리
# ============================================================================

@router.post("/tokens", status_code=201, response_model=FcmTokenResponse)
async def register_fcm_token(
    request: Request,
    data: FcmTokenRegister,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """FCM 토큰 등록"""
    service = PushService(db)
    user_id = UUID(auth.user_id)
    await enforce_user_rate_limit(
        user_id=auth.user_id,
        scope="push:register_token",
        limit=20,
        window_seconds=60,
        detail="푸시 토큰 등록 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
    )

    try:
        token = data.token.strip()
        platform = data.platform.strip().lower()
        device_name = data.device_name.strip() if data.device_name else None

        if not token or not platform:
            raise HTTPException(400, "token과 platform은 필수입니다")

        if platform not in ["android", "ios", "web"]:
            raise HTTPException(400, "platform은 android, ios, web 중 하나여야 합니다")

        fcm_token = await service.register_token(
            user_id=user_id,
            token=token,
            platform=platform,
            device_name=device_name,
        )

        return {
            "id": str(fcm_token.id),
            "token": fcm_token.token,
            "platform": fcm_token.platform,
            "device_name": fcm_token.device_name,
            "is_active": fcm_token.is_active,
            "created_at": fcm_token.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/tokens/{token_id}", status_code=200, response_model=FcmTokenResponse)
async def update_fcm_token(
    request: Request,
    token_id: UUID,
    data: FcmTokenUpdate,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """FCM 토큰 업데이트"""
    service = PushService(db)
    user_id = UUID(auth.user_id)
    await enforce_user_rate_limit(
        user_id=auth.user_id,
        scope="push:update_token",
        limit=20,
        window_seconds=60,
        detail="푸시 토큰 수정 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
    )

    try:
        platform = data.platform.strip().lower() if data.platform else None

        if not platform:
            raise HTTPException(400, "platform은 필수입니다")

        device_name = data.device_name.strip() if data.device_name else None
        fcm_token = await service.update_token(
            user_id,
            token_id,
            platform,
            device_name=device_name,
        )

        if not fcm_token:
            raise HTTPException(404, "토큰을 찾을 수 없습니다")

        return {
            "id": str(fcm_token.id),
            "token": fcm_token.token,
            "platform": fcm_token.platform,
            "device_name": fcm_token.device_name,
            "is_active": fcm_token.is_active,
            "created_at": fcm_token.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/tokens/{token}", status_code=204)
async def remove_fcm_token(
    request: Request,
    token: str,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """FCM 토큰 삭제"""
    service = PushService(db)
    user_id = UUID(auth.user_id)
    await enforce_user_rate_limit(
        user_id=auth.user_id,
        scope="push:remove_token",
        limit=20,
        window_seconds=60,
        detail="푸시 토큰 삭제 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
    )

    try:
        success = await service.remove_token(user_id, token.strip())

        if not success:
            raise HTTPException(404, "토큰을 찾을 수 없습니다")

        return None
    except ValueError as e:
        raise HTTPException(400, str(e))


# ============================================================================
# 알림 히스토리
# ============================================================================

@router.get("/notifications", response_model=dict)
async def get_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """사용자의 알림 목록 조회"""
    service = PushService(db)
    user_id = UUID(auth.user_id)

    try:
        notifications, total = await service.get_notifications(
            user_id=user_id,
            page=page,
            limit=limit,
        )

        items = [
            {
                "id": str(notif.id),
                "title": notif.title,
                "body": notif.body,
                "event_type": notif.event_type,
                "related_id": str(notif.related_id) if notif.related_id else None,
                "is_read": notif.is_read,
                "created_at": notif.created_at.isoformat(),
                "sent_at": notif.sent_at.isoformat() if notif.sent_at else None,
            }
            for notif in notifications
        ]

        return PaginatedResponse.create(items, total, page, limit).__dict__
    except Exception as e:
        raise HTTPException(500, f"알림을 불러오지 못했습니다: {e}")


@router.get("/notifications/unread/count", response_model=dict)
async def get_unread_count(
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """읽지 않은 알림 개수"""
    service = PushService(db)
    user_id = UUID(auth.user_id)

    try:
        count = await service.get_unread_count(user_id)
        return {"unread_count": count}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("/notifications/{notification_id}/read", status_code=200)
async def mark_notification_as_read(
    request: Request,
    notification_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """알림을 읽음으로 표시"""
    service = PushService(db)
    user_id = UUID(auth.user_id)
    await enforce_user_rate_limit(
        user_id=auth.user_id,
        scope="push:mark_read",
        limit=60,
        window_seconds=60,
        detail="알림 읽음 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
    )

    try:
        success = await service.mark_as_read(user_id, notification_id)

        if not success:
            raise HTTPException(404, "알림을 찾을 수 없습니다")

        return {"read": True}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("/notifications/read-all", status_code=200)
async def mark_all_as_read(
    request: Request,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """모든 알림을 읽음으로 표시"""
    service = PushService(db)
    user_id = UUID(auth.user_id)
    await enforce_user_rate_limit(
        user_id=auth.user_id,
        scope="push:mark_all_read",
        limit=20,
        window_seconds=60,
        detail="알림 일괄 읽음 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
    )

    try:
        count = await service.mark_all_as_read(user_id)
        return {"marked_count": count}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/notifications/{notification_id}", status_code=204)
async def delete_notification(
    request: Request,
    notification_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """알림 삭제"""
    service = PushService(db)
    user_id = UUID(auth.user_id)
    await enforce_user_rate_limit(
        user_id=auth.user_id,
        scope="push:delete_notification",
        limit=30,
        window_seconds=60,
        detail="알림 삭제 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
    )

    try:
        success = await service.delete_notification(user_id, notification_id)
        if not success:
            raise HTTPException(404, "알림을 찾을 수 없습니다")
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/notifications/{notification_id}", status_code=204)
async def delete_notification(
    request: Request,
    notification_id: UUID,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """알림 삭제"""
    service = PushService(db)
    await enforce_user_rate_limit(
        user_id=auth.user_id,
        scope="push:delete_notification",
        limit=60,
        window_seconds=60,
        detail="알림 삭제 요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
    )

    try:
        success = await service.delete_notification(notification_id)

        if not success:
            raise HTTPException(404, "알림을 찾을 수 없습니다")

        return None
    except Exception as e:
        raise HTTPException(500, str(e))
