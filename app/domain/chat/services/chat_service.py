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
        """사용자 채팅방 목록 (기본)"""
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

    async def list_rooms_with_details(
        self, user_id: UUID, page: int = 1, limit: int = 20
    ) -> Tuple[List[dict], int]:
        """
        사용자 채팅방 목록 (상대 정보, 마지막 메시지 포함)

        Returns:
            [
                {
                    "room_id": str,
                    "name": str,
                    "is_group": bool,
                    "participants": [{ "user_id", "name", "picture", "username" }],
                    "last_message": { "content", "sender_name", "created_at" },
                    "unread_count": int,
                    "updated_at": str,
                }
            ]
        """
        from app.domain.auth.models.user import User
        from sqlalchemy import func as sa_func

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
            select(sa_func.count())
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

        result_list = []
        for room in rooms:
            # 1. 참여자 정보 조회
            member_result = await self.db.execute(
                select(User)
                .join(ChatRoomMember)
                .where(
                    and_(
                        ChatRoomMember.room_id == room.id,
                        ChatRoomMember.is_deleted.is_(False),
                    )
                )
            )
            members = list(member_result.scalars().all())
            participants = [
                {
                    "user_id": str(m.id),
                    "name": m.name,
                    "picture": m.picture,
                    "username": m.username,
                }
                for m in members
            ]

            # 2. 마지막 메시지 조회
            msg_result = await self.db.execute(
                select(ChatMessage)
                .where(
                    and_(
                        ChatMessage.room_id == room.id,
                        ChatMessage.is_deleted.is_(False),
                    )
                )
                .order_by(ChatMessage.created_at.desc())
                .limit(1)
            )
            last_msg = msg_result.scalar_one_or_none()
            last_message = None
            if last_msg:
                sender = await self.db.execute(
                    select(User).where(User.id == last_msg.sender_id)
                )
                sender_user = sender.scalar_one_or_none()
                last_message = {
                    "content": last_msg.content,
                    "sender_name": sender_user.name if sender_user else "Unknown",
                    "created_at": last_msg.created_at.isoformat(),
                }

            # 3. 읽지 않은 메시지 수 (향후 구현 - 지금은 0)
            unread_count = 0

            result_list.append(
                {
                    "room_id": str(room.id),
                    "name": room.name,
                    "is_group": room.is_group,
                    "participants": participants,
                    "last_message": last_message,
                    "unread_count": unread_count,
                    "updated_at": room.updated_at.isoformat(),
                }
            )

        return result_list, total

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

    async def get_or_create_one_to_one_room(
        self, user_a_id: UUID, user_b_id: UUID
    ) -> ChatRoom:
        """
        1:1 채팅방 생성 또는 기존 방 반환

        같은 두 user_id 조합으로는 오직 하나의 room만 존재함을 보장.
        이미 존재하면 기존 room_id 반환, 없으면 새로 생성.

        Args:
            user_a_id: 사용자 A (보통 현재 사용자)
            user_b_id: 사용자 B (상대방)

        Returns:
            ChatRoom 객체
        """
        # 두 user를 정렬하여 일관성 유지
        # (LEAST/GREATEST는 PostgreSQL 함수, SQLAlchemy에서는 min/max 사용)
        user_ids = sorted([user_a_id, user_b_id])
        user_1, user_2 = user_ids[0], user_ids[1]

        # 기존 1:1 방 조회
        # is_group=False 이고, 두 사용자가 모두 멤버인 경우
        result = await self.db.execute(
            select(ChatRoom)
            .where(
                and_(
                    ChatRoom.is_group.is_(False),
                    ChatRoom.is_deleted.is_(False),
                    ChatRoom.id.in_(
                        select(ChatRoomMember.room_id).where(
                            and_(
                                ChatRoomMember.user_id == user_1,
                                ChatRoomMember.is_deleted.is_(False),
                            )
                        )
                    ),
                )
            )
        )

        existing_rooms = list(result.scalars().all())
        for room in existing_rooms:
            # 이 room에 user_2도 멤버인지 확인
            member_result = await self.db.execute(
                select(ChatRoomMember.id).where(
                    and_(
                        ChatRoomMember.room_id == room.id,
                        ChatRoomMember.user_id == user_2,
                        ChatRoomMember.is_deleted.is_(False),
                    )
                )
            )
            if member_result.scalar_one_or_none():
                # 기존 room 발견
                return room

        # 새로운 1:1 room 생성
        room = ChatRoom(
            name=f"1:1 Chat",  # UI에서 상대방 이름으로 표시 예정
            is_group=False,
            created_by=user_a_id,
        )
        self.db.add(room)
        await self.db.flush()

        # 두 사용자 모두 멤버로 추가
        for user_id in [user_1, user_2]:
            self.db.add(
                ChatRoomMember(
                    room_id=room.id,
                    user_id=user_id,
                    role="owner" if user_id == user_a_id else "member",
                )
            )

        await self.db.commit()
        await self.db.refresh(room)

        await event_bus.emit(
            ChatRoomCreatedEvent(
                room_id=str(room.id),
                created_by=str(user_a_id),
                member_count=2,
                is_group=False,
            )
        )
        return room
