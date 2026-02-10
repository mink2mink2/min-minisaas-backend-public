"""채팅 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from features.chat.backend.services.chat_service import ChatService

router = APIRouter()

@router.get("/rooms")
async def get_rooms(db: AsyncSession = Depends(get_db)):
    """채팅방 목록"""
    service = ChatService(db)
    rooms = await service.get_rooms("dummy-user")  # TODO: 실제 user_id
    return {"rooms": [{"id": str(r.id), "name": r.name} for r in rooms]}

@router.post("/rooms")
async def create_room(name: str, db: AsyncSession = Depends(get_db)):
    """채팅방 생성"""
    service = ChatService(db)
    room = await service.create_room(name, "dummy-user")  # TODO: 실제 user_id
    return {"room_id": str(room.id), "name": room.name}

@router.get("/rooms/{room_id}/messages")
async def get_messages(room_id: str, db: AsyncSession = Depends(get_db)):
    """메시지 조회"""
    service = ChatService(db)
    messages = await service.get_messages(room_id)
    return {"messages": [{"id": str(m.id), "content": m.content} for m in messages]}