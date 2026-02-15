"""채팅 API 엔드포인트"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import verify_api_key
from app.api.v1.dependencies.auth import AuthResult, verify_any_platform
from app.core.auth.firebase_verifier import firebase_verifier
from app.core.auth.session_manager import session_manager
from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.security import decode_token
from app.domain.auth.models.user import User
from app.domain.chat.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatRoomCreate,
    ChatRoomResponse,
)
from app.domain.chat.services.chat_service import ChatService
from app.domain.chat.services.realtime_gateway import chat_realtime_gateway
from app.schemas.response import PaginatedResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/rooms", response_model=dict)
async def list_rooms(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """내 채팅방 목록"""
    user_id = UUID(auth.user_id)
    service = ChatService(db)
    rooms, total = await service.list_rooms(user_id=user_id, page=page, limit=limit)

    items = []
    for room in rooms:
        member_count = await service.get_room_member_count(room.id)
        items.append(
            ChatRoomResponse(
                id=room.id,
                name=room.name,
                is_group=room.is_group,
                created_by=room.created_by,
                member_count=member_count,
                created_at=room.created_at,
                updated_at=room.updated_at,
            )
        )

    return PaginatedResponse.create(items, total, page, limit).__dict__


@router.post("/rooms", response_model=ChatRoomResponse, status_code=201)
async def create_room(
    data: ChatRoomCreate,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """채팅방 생성"""
    user_id = UUID(auth.user_id)
    service = ChatService(db)

    room, member_count = await service.create_room(
        creator_id=user_id,
        name=data.name,
        is_group=data.is_group,
        member_ids=data.member_ids,
    )
    return ChatRoomResponse(
        id=room.id,
        name=room.name,
        is_group=room.is_group,
        created_by=room.created_by,
        member_count=member_count,
        created_at=room.created_at,
        updated_at=room.updated_at,
    )


@router.get("/rooms/{room_id}/messages", response_model=dict)
async def list_messages(
    room_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """채팅방 메시지 목록"""
    service = ChatService(db)
    try:
        messages, total = await service.list_messages(
            room_id=room_id,
            user_id=UUID(auth.user_id),
            page=page,
            limit=limit,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not a room member")

    items = [
        ChatMessageResponse(
            id=message.id,
            room_id=message.room_id,
            sender_id=message.sender_id,
            content=message.content,
            message_type=message.message_type,
            created_at=message.created_at,
            updated_at=message.updated_at,
        )
        for message in messages
    ]
    return PaginatedResponse.create(items, total, page, limit).__dict__


@router.post("/rooms/{room_id}/messages", response_model=ChatMessageResponse, status_code=201)
async def send_message(
    room_id: UUID,
    data: ChatMessageCreate,
    auth: AuthResult = Depends(verify_any_platform),
    _: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    """메시지 전송"""
    service = ChatService(db)
    try:
        message = await service.send_message(
            room_id=room_id,
            sender_id=UUID(auth.user_id),
            content=data.content,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not a room member")

    return ChatMessageResponse(
        id=message.id,
        room_id=message.room_id,
        sender_id=message.sender_id,
        content=message.content,
        message_type=message.message_type,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


async def _resolve_websocket_user_id(
    websocket: WebSocket,
    db: AsyncSession,
) -> Optional[UUID]:
    """웹소켓 요청 헤더로 사용자 식별"""
    x_api_key = websocket.headers.get("x-api-key")
    if x_api_key != settings.API_SECRET_KEY:
        return None

    platform = websocket.headers.get("x-platform")
    authorization = websocket.headers.get("authorization")

    if platform == "web":
        session_id = websocket.cookies.get("session")
        if not session_id:
            return None
        session_data = await session_manager.validate_and_slide(session_id)
        if not session_data:
            return None
        return UUID(session_data["user_id"])

    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:]
    if platform == "mobile":
        payload = await firebase_verifier.verify(token)
        firebase_uid = payload.get("sub")
        if not firebase_uid:
            return None
        result = await db.execute(select(User.id).where(User.firebase_uid == firebase_uid))
        user_id = result.scalar_one_or_none()
        return user_id

    if platform in ("desktop", "device"):
        payload = decode_token(token)
        subject = payload.get("sub")
        return UUID(subject) if subject else None

    return None


@router.websocket("/ws/rooms/{room_id}")
async def room_websocket(room_id: UUID, websocket: WebSocket):
    """
    채팅방 웹소켓

    - Header: X-API-Key, X-Platform, Authorization (or web session cookie)
    - Client message format: {"content": "..."}
    """
    async with AsyncSessionLocal() as db:
        user_id: Optional[UUID] = None
        try:
            user_id = await _resolve_websocket_user_id(websocket, db)
            if not user_id:
                await websocket.close(code=1008)
                return

            service = ChatService(db)
            if not await service.is_room_member(room_id=room_id, user_id=user_id):
                await websocket.close(code=1008)
                return

            await chat_realtime_gateway.connect(room_id, websocket)
            while True:
                payload = await websocket.receive_json()
                content = str(payload.get("content", "")).strip()
                if not content:
                    continue
                await service.send_message(
                    room_id=room_id,
                    sender_id=user_id,
                    content=content,
                )

        except WebSocketDisconnect:
            pass
        except Exception:
            try:
                await websocket.close(code=1011)
            except Exception:
                pass
        finally:
            if user_id:
                chat_realtime_gateway.disconnect(room_id, websocket)
