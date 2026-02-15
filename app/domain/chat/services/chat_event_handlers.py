"""채팅 도메인 이벤트 핸들러"""
import logging
from uuid import UUID

from app.core.events import Event
from app.domain.chat.services.realtime_gateway import chat_realtime_gateway

logger = logging.getLogger(__name__)


class ChatEventHandlers:
    """채팅 이벤트 핸들러 모음"""

    @staticmethod
    async def handle_room_created(event: Event) -> None:
        logger.info(
            "chat.room.created room_id=%s created_by=%s member_count=%s",
            event.payload.get("room_id"),
            event.payload.get("created_by"),
            event.payload.get("member_count"),
        )

    @staticmethod
    async def handle_message_created(event: Event) -> None:
        room_id = event.payload.get("room_id")
        if not room_id:
            return

        await chat_realtime_gateway.broadcast_json(
            UUID(room_id),
            {
                "event_type": "chat.message.created",
                "room_id": room_id,
                "message": {
                    "id": event.payload.get("message_id"),
                    "room_id": room_id,
                    "sender_id": event.payload.get("sender_id"),
                    "content": event.payload.get("content"),
                    "message_type": event.payload.get("message_type", "text"),
                    "created_at": event.payload.get("created_at"),
                },
            },
        )


async def register_chat_event_handlers(event_bus) -> None:
    """채팅 이벤트 핸들러 등록"""
    event_bus.subscribe("chat.room.created", ChatEventHandlers.handle_room_created)
    event_bus.subscribe("chat.message.created", ChatEventHandlers.handle_message_created)
    logger.info("✅ 채팅 이벤트 핸들러 등록 완료")
