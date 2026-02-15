"""채팅 비즈니스 로직"""
from typing import List, Sequence, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import ChatMessageCreatedEvent, ChatRoomCreatedEvent, event_bus
from app.domain.chat.models.message import ChatMessage
from app.domain.chat.models.room import ChatRoom, ChatRoomMember


class ChatService:
    """채팅 도메인 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_room(
        self,
        creator_id: UUID,
        name: str,
        is_group: bool = False,
        member_ids: Sequence[UUID] = (),
    ) -> Tuple[ChatRoom, int]:
        """채팅방 생성"""
        normalized_member_ids = set(member_ids)
        normalized_member_ids.add(creator_id)

        room = ChatRoom(
            name=name.strip(),
            is_group=is_group,
            created_by=creator_id,
        )
        self.db.add(room)
        await self.db.flush()

        for member_id in normalized_member_ids:
            self.db.add(
                ChatRoomMember(
                    room_id=room.id,
                    user_id=member_id,
                    role="owner" if member_id == creator_id else "member",
                )
            )

        await self.db.commit()
        await self.db.refresh(room)
        member_count = len(normalized_member_ids)

        await event_bus.emit(
            ChatRoomCreatedEvent(
                room_id=str(room.id),
                created_by=str(creator_id),
                member_count=member_count,
                is_group=is_group,
            )
        )
        return room, member_count

    async def list_rooms(
        self, user_id: UUID, page: int = 1, limit: int = 20
    ) -> Tuple[List[ChatRoom], int]:
        """사용자 채팅방 목록"""
        membership_subquery = (
            select(ChatRoomMember.room_id)
            .where(
                and_(
                    ChatRoomMember.user_id == user_id,
                    ChatRoomMember.is_deleted.is_(False),
                )
            )
            .subquery()
        )

        count_result = await self.db.execute(
            select(func.count())
            .select_from(ChatRoom)
            .where(
                and_(
                    ChatRoom.id.in_(select(membership_subquery.c.room_id)),
                    ChatRoom.is_deleted.is_(False),
                )
            )
        )
        total = count_result.scalar() or 0

        offset = (page - 1) * limit
        room_result = await self.db.execute(
            select(ChatRoom)
            .where(
                and_(
                    ChatRoom.id.in_(select(membership_subquery.c.room_id)),
                    ChatRoom.is_deleted.is_(False),
                )
            )
            .order_by(ChatRoom.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rooms = list(room_result.scalars().all())
        return rooms, total

    async def get_room_member_count(self, room_id: UUID) -> int:
        """채팅방 멤버 수"""
        result = await self.db.execute(
            select(func.count())
            .select_from(ChatRoomMember)
            .where(
                and_(
                    ChatRoomMember.room_id == room_id,
                    ChatRoomMember.is_deleted.is_(False),
                )
            )
        )
        return result.scalar() or 0

    async def is_room_member(self, room_id: UUID, user_id: UUID) -> bool:
        """사용자 멤버십 확인"""
        result = await self.db.execute(
            select(ChatRoomMember.id).where(
                and_(
                    ChatRoomMember.room_id == room_id,
                    ChatRoomMember.user_id == user_id,
                    ChatRoomMember.is_deleted.is_(False),
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def send_message(self, room_id: UUID, sender_id: UUID, content: str) -> ChatMessage:
        """메시지 전송"""
        if not await self.is_room_member(room_id, sender_id):
            raise PermissionError("Not a room member")

        message = ChatMessage(
            room_id=room_id,
            sender_id=sender_id,
            content=content.strip(),
            message_type="text",
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)

        await event_bus.emit(
            ChatMessageCreatedEvent(
                room_id=str(room_id),
                message_id=str(message.id),
                sender_id=str(sender_id),
                content=message.content,
                message_type=message.message_type,
                created_at=message.created_at.isoformat(),
            )
        )
        return message

    async def list_messages(
        self,
        room_id: UUID,
        user_id: UUID,
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[ChatMessage], int]:
        """채팅방 메시지 목록"""
        if not await self.is_room_member(room_id, user_id):
            raise PermissionError("Not a room member")

        count_result = await self.db.execute(
            select(func.count())
            .select_from(ChatMessage)
            .where(
                and_(
                    ChatMessage.room_id == room_id,
                    ChatMessage.is_deleted.is_(False),
                )
            )
        )
        total = count_result.scalar() or 0

        offset = (page - 1) * limit
        result = await self.db.execute(
            select(ChatMessage)
            .where(
                and_(
                    ChatMessage.room_id == room_id,
                    ChatMessage.is_deleted.is_(False),
                )
            )
            .order_by(ChatMessage.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()
        return messages, total
