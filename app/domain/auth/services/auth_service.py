"""인증 서비스 - 공통 비즈니스 로직"""
from typing import Tuple, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.auth.models.user import User
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.cache import cache


class AuthService:
    """인증 관련 공통 비즈니스 로직 - 모든 플랫폼에서 공유"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        picture: Optional[str] = None,
    ) -> Tuple[User, bool]:
        """
        유저 조회 또는 생성 (Firebase/OAuth 기반)

        Args:
            user_id: 외부 인증제공자의 user_id (Firebase UID 등)
            email: 이메일
            name: 사용자 이름
            picture: 프로필 사진 URL

        Returns:
            (user, is_new_user) tuple
        """
        # Firebase UID로 조회
        result = await self.db.execute(
            select(User).where(User.firebase_uid == user_id)
        )
        user = result.scalar_one_or_none()

        if user:
            # 기존 사용자
            # last_login 업데이트
            user.last_login = datetime.utcnow()

            # 프로필 정보 갱신
            if email:
                user.email = email
            if name:
                user.name = name
            if picture:
                user.picture = picture

            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            return user, False

        # 신규 사용자 생성
        user = User(
            firebase_uid=user_id,
            email=email or "",
            name=name or "User",
            picture=picture,
            points=10,  # 가입 보너스
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user, True

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """사용자 ID로 조회"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        """Firebase UID로 조회"""
        result = await self.db.execute(
            select(User).where(User.firebase_uid == firebase_uid)
        )
        return result.scalar_one_or_none()

    async def deactivate_user(self, user_id: str) -> bool:
        """계정 비활성화 (soft delete)"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = False
        self.db.add(user)
        await self.db.commit()
        return True

    # 레거시 메서드들 (이메일+비밀번호 인증용)
    async def register(self, email: str, password: str) -> User:
        """회원가입"""
        user = User(
            email=email,
            password_hash=hash_password(password),
            name="User",
            points=10,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def login(
        self,
        email: str,
        password: str,
        client_type: str = "web",
        user_agent: str = None,
        ip: str = None,
    ) -> Optional[dict]:
        """로그인 - 토큰 반환"""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            return None

        access_token = create_access_token(str(user.id), client_type=client_type)
        refresh_token = create_refresh_token(str(user.id), client_type=client_type)

        # 보안 강화: Redis에 현재 활성 토큰 및 기기 정보 저장
        session_key = f"auth:session:{user.id}:{client_type}"
        session_data = {"access": access_token, "refresh": refresh_token, "ua": user_agent, "ip": ip}
        ttl = 3600 if client_type == "web" else 86400 * 7
        await cache.set(session_key, session_data, ttl_seconds=ttl)

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

    async def refresh_token(
        self, refresh_token: str, user_agent: str = None, ip: str = None
    ) -> Optional[dict]:
        """토큰 갱신 (Refresh Token Rotation 적용)"""
        try:
            from app.core.security import decode_token

            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                return None

            user_id = payload.get("sub")
            client_type = payload.get("client")

            # Redis 세션 확인
            session_key = f"auth:session:{user_id}:{client_type}"
            session_data = await cache.get(session_key)

            # 리프레시 토큰 일치 여부 확인
            if not session_data or session_data.get("refresh") != refresh_token:
                await cache.delete(session_key)
                return None

            # 새 토큰 발급
            new_access = create_access_token(user_id, client_type=client_type)
            new_refresh = create_refresh_token(user_id, client_type=client_type)

            # Redis 업데이트
            session_data.update({"access": new_access, "refresh": new_refresh, "ua": user_agent, "ip": ip})
            ttl = 3600 if client_type == "web" else 86400 * 7
            await cache.set(session_key, session_data, ttl_seconds=ttl)

            return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}
        except Exception:
            return None

    async def search_users(
        self, query: str, exclude_user_id: Optional[str] = None, limit: int = 10
    ) -> list:
        """
        사용자 검색 (사용자명 또는 이메일)

        Args:
            query: 검색어 (최소 2글자)
            exclude_user_id: 제외할 사용자 ID (보통 현재 사용자)
            limit: 최대 결과 수

        Returns:
            User 리스트 (id, name, picture, username, email)
        """
        if len(query.strip()) < 2:
            return []

        query = query.strip().lower()

        # 사용자명 또는 이메일로 검색
        from sqlalchemy import or_, and_

        conditions = [
            User.is_active.is_(True),
            or_(
                User.username.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%"),
                User.name.ilike(f"%{query}%"),
            ),
        ]

        # 자신 제외
        if exclude_user_id:
            conditions.append(User.id != exclude_user_id)

        result = await self.db.execute(
            select(User)
            .where(and_(*conditions))
            .limit(limit)
        )

        users = result.scalars().all()
        return [
            {
                "id": str(user.id),
                "name": user.name,
                "picture": user.picture,
                "username": user.username,
                "email": user.email,
            }
            for user in users
        ]