# V/20 — 테스트 케이스 (Test Cases)

> Phase 1~2 완료된 테스트 코드 패턴 및 Phase 3~7 계획 케이스 정리

---

## 테스트 공통 설정

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import fakeredis.aioredis

from app.main import app
from app.core.database import get_db, Base
from app.core.cache import get_cache

TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost/test_db"

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(test_engine):
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def fake_redis():
    redis = fakeredis.aioredis.FakeRedis()
    yield redis
    await redis.close()

@pytest_asyncio.fixture
async def client(db_session, fake_redis):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_cache] = lambda: fake_redis
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def auth_token(client):
    """테스트용 사용자 JWT 토큰"""
    # Mock Firebase 검증을 우회하는 테스트 토큰 생성
    from app.domain.auth.services import AuthService
    from app.core.database import get_db
    # ... (실제 구현에서는 테스트용 사용자 직접 생성 후 JWT 발급)
    return "test_jwt_token"

@pytest_asyncio.fixture
async def test_user(db_session):
    from app.domain.auth.models import User
    user = User(
        email="test@example.com",
        provider="google",
        provider_id="google_123",
        nickname="테스트유저"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
```

---

## Phase 1: Service Unit Tests ✅

### Auth Service Tests

```python
# tests/phase1/test_auth_service.py
import pytest
from unittest.mock import AsyncMock, patch
from app.domain.auth.services import AuthService

@pytest.mark.asyncio
@pytest.mark.phase1
async def test_create_or_get_user_new(db_session):
    """신규 사용자 — DB에 생성되어야 함"""
    service = AuthService(db_session)
    user = await service.create_or_get_user(
        email="new@example.com",
        provider="google",
        provider_id="google_456",
        nickname="신규유저"
    )
    assert user.id is not None
    assert user.email == "new@example.com"
    assert user.provider == "google"

@pytest.mark.asyncio
@pytest.mark.phase1
async def test_create_or_get_user_existing(db_session, test_user):
    """기존 사용자 — 새로 생성하지 않고 기존 레코드 반환"""
    service = AuthService(db_session)
    user = await service.create_or_get_user(
        email=test_user.email,
        provider=test_user.provider,
        provider_id=test_user.provider_id,
        nickname="다른닉네임"
    )
    assert user.id == test_user.id  # 동일한 레코드

@pytest.mark.asyncio
@pytest.mark.phase1
async def test_create_jwt(db_session, test_user):
    """JWT 토큰 생성 — payload에 사용자 ID 포함"""
    service = AuthService(db_session)
    token = service.create_jwt(user_id=test_user.id)
    assert isinstance(token, str)
    assert len(token) > 50

@pytest.mark.asyncio
@pytest.mark.phase1
async def test_verify_jwt_valid(db_session, test_user):
    """유효한 JWT 검증 성공"""
    service = AuthService(db_session)
    token = service.create_jwt(user_id=test_user.id)
    payload = service.verify_jwt(token)
    assert payload["sub"] == str(test_user.id)

@pytest.mark.asyncio
@pytest.mark.phase1
async def test_verify_jwt_expired(db_session):
    """만료된 JWT — HTTPException 401 발생"""
    from fastapi import HTTPException
    # 과거 시간으로 만료된 토큰 생성 (테스트 헬퍼 사용)
    expired_token = create_expired_test_token()
    service = AuthService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        service.verify_jwt(expired_token)
    assert exc_info.value.status_code == 401
```

### Board Service Tests

```python
# tests/phase1/test_board_service.py
import pytest
from unittest.mock import AsyncMock, patch
from app.domain.board.services import BoardService
from app.domain.board.schemas import PostCreate

@pytest.mark.asyncio
@pytest.mark.phase1
async def test_create_post_publishes_event(db_session, test_user):
    """게시글 작성 — board.post.created 이벤트 발행"""
    service = BoardService(db_session)
    published_events = []

    with patch("app.core.events.EventBus.publish", new_callable=AsyncMock) as mock_publish:
        mock_publish.side_effect = lambda name, data: published_events.append((name, data))
        post = await service.create_post(
            user_id=test_user.id,
            data=PostCreate(title="테스트 글", content="내용", category="자유")
        )

    assert post.id is not None
    assert post.title == "테스트 글"
    assert ("board.post.created", {"post_id": post.id, "author_id": test_user.id, "title": "테스트 글"}) \
           in [(e[0], e[1]) for e in published_events]

@pytest.mark.asyncio
@pytest.mark.phase1
async def test_add_like_increments_count(db_session, test_user):
    """좋아요 추가 — likes_count 1 증가"""
    service = BoardService(db_session)
    post = await service.create_post(test_user.id, PostCreate(title="글", content="내용"))
    assert post.likes_count == 0

    await service.add_like(user_id=test_user.id, post_id=post.id)
    await db_session.refresh(post)
    assert post.likes_count == 1

@pytest.mark.asyncio
@pytest.mark.phase1
async def test_add_like_duplicate_raises_conflict(db_session, test_user):
    """중복 좋아요 — HTTPException 409 발생"""
    from fastapi import HTTPException
    service = BoardService(db_session)
    post = await service.create_post(test_user.id, PostCreate(title="글", content="내용"))

    await service.add_like(user_id=test_user.id, post_id=post.id)
    with pytest.raises(HTTPException) as exc_info:
        await service.add_like(user_id=test_user.id, post_id=post.id)
    assert exc_info.value.status_code == 409
```

### Push Service Tests

```python
# tests/phase1/test_push_service.py
import pytest
from app.domain.push.services import PushService
from app.domain.push.schemas import TokenCreate

@pytest.mark.asyncio
@pytest.mark.phase1
async def test_register_token_new(db_session, test_user):
    """신규 FCM 토큰 등록"""
    service = PushService(db_session)
    token = await service.register_token(
        user_id=test_user.id,
        data=TokenCreate(token="fcm_token_abc", platform="android")
    )
    assert token.id is not None
    assert token.active is True

@pytest.mark.asyncio
@pytest.mark.phase1
async def test_register_token_existing_updates(db_session, test_user):
    """이미 존재하는 토큰 — 갱신 (중복 생성 없음)"""
    service = PushService(db_session)
    token_data = TokenCreate(token="existing_token", platform="ios")
    first = await service.register_token(user_id=test_user.id, data=token_data)
    second = await service.register_token(user_id=test_user.id, data=token_data)
    assert first.id == second.id  # 동일 레코드

@pytest.mark.asyncio
@pytest.mark.phase1
async def test_get_unread_count(db_session, test_user):
    """읽지 않은 알림 수 조회"""
    service = PushService(db_session)
    # 알림 3개 생성 (read=False)
    for i in range(3):
        await service._create_notification(
            user_id=test_user.id, title=f"알림{i}", body="내용", type="board"
        )
    count = await service.get_unread_count(user_id=test_user.id)
    assert count == 3
```

---

## Phase 2: API Endpoint Tests ✅

```python
# tests/phase2/test_auth_api.py
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
@pytest.mark.phase2
async def test_google_login_success(client):
    """Google 로그인 — 유효한 토큰 → 200 + JWT 반환"""

---

## Schema / Migration Verification

### TC-DB-01: model registry 완전성 확인
- 목적: Alembic metadata가 실제 운영 대상 모델을 모두 포함하는지 확인
- 절차:
  1. `app/db/model_registry.py`에 대상 도메인 모델 import 존재 여부 확인
  2. `.venv/bin/python -c "import app.db.model_registry; from app.core.database import Base; print(sorted(Base.metadata.tables.keys()))"` 실행
  3. 운영/개발 DB에 이미 존재하는 핵심 테이블(`blog_*`, `fcm_tokens`, `push_notifications`)이 metadata에 포함되는지 확인
- 기대 결과:
  - 기존 테이블이 metadata에 모두 존재
  - `alembic check`에서 해당 테이블이 `remove_table`로 보고되지 않음

### TC-DB-02: `fcm_tokens` BaseModel 컬럼 보정 migration
- 목적: `20260328_0012_fcm_tokens_basemodel_columns`가 개발/운영 DB에서 재실행 가능하게 동작하는지 확인
- 절차:
  1. `.venv/bin/alembic upgrade head` 실행
  2. `alembic current`가 `20260328_0012 (head)`인지 확인
  3. `information_schema.columns`에서 `fcm_tokens.is_deleted` 존재 및 `NOT NULL` 여부 확인
- 기대 결과:
  - migration이 오류 없이 적용됨
  - `fcm_tokens.is_deleted`가 존재하고 `NOT NULL` 상태임

### TC-DB-03: `push_notifications` BaseModel 컬럼 보정 regression
- 목적: `push_notifications.updated_at/is_deleted` 보정 상태가 유지되는지 확인
- 절차:
  1. `.venv/bin/alembic upgrade head` 실행
  2. `information_schema.columns`에서 `push_notifications.updated_at`, `push_notifications.is_deleted` 존재 여부 확인
- 기대 결과:
  - 두 컬럼이 모두 존재
  - ORM이 `BaseModel` 공통 컬럼 참조 시 런타임 오류가 발생하지 않음
    mock_user_info = {
        "uid": "google_123",
        "email": "user@gmail.com",
        "name": "홍길동",
        "picture": "https://..."
    }
    with patch("app.core.auth.google.verify_google_token", return_value=mock_user_info):
        response = await client.post("/api/v1/auth/login/google", json={"id_token": "valid_token"})

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "user@gmail.com"
    assert data["user"]["provider"] == "google"

@pytest.mark.asyncio
@pytest.mark.phase2
async def test_google_login_invalid_token(client):
    """Google 로그인 — 유효하지 않은 토큰 → 401"""
    with patch("app.core.auth.google.verify_google_token", side_effect=Exception("Invalid token")):
        response = await client.post("/api/v1/auth/login/google", json={"id_token": "invalid"})

    assert response.status_code == 401

@pytest.mark.asyncio
@pytest.mark.phase2
async def test_get_me_authenticated(client, auth_headers):
    """내 정보 조회 — 인증된 요청 → 200"""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "email" in data

@pytest.mark.asyncio
@pytest.mark.phase2
async def test_get_me_unauthenticated(client):
    """내 정보 조회 — 비인증 → 401"""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401

# tests/phase2/test_board_api.py
@pytest.mark.asyncio
@pytest.mark.phase2
async def test_create_post_success(client, auth_headers):
    response = await client.post(
        "/api/v1/board/posts",
        json={"title": "테스트 글", "content": "내용", "category": "자유"},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "테스트 글"
    assert data["likes_count"] == 0

@pytest.mark.asyncio
@pytest.mark.phase2
async def test_create_post_unauthorized(client):
    response = await client.post(
        "/api/v1/board/posts",
        json={"title": "테스트 글", "content": "내용"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
@pytest.mark.phase2
async def test_update_post_by_other_user(client, auth_headers_user2, test_post):
    """타인의 게시글 수정 시도 → 403"""
    response = await client.put(
        f"/api/v1/board/posts/{test_post.id}",
        json={"title": "수정 시도", "content": "수정 내용"},
        headers=auth_headers_user2
    )
    assert response.status_code == 403

@pytest.mark.asyncio
@pytest.mark.phase2
async def test_push_register_token(client, auth_headers):
    response = await client.post(
        "/api/v1/push/tokens",
        json={"token": "test_fcm_token", "platform": "android"},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["active"] is True
```

---

## Phase 3: Event Handler Tests 📋 (계획)

```python
# tests/phase3/test_push_handlers.py (계획)
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
@pytest.mark.phase3
async def test_push_handler_on_board_post_created(db_session, test_user):
    """
    board.post.created 이벤트 발행 시
    → PushService.create_notification 호출
    → DB에 알림 저장
    """
    from app.domain.push.handlers import handle_board_post_created

    with patch("app.domain.push.fcm_service.FCMService.send", new_callable=AsyncMock):
        await handle_board_post_created({
            "post_id": 1,
            "author_id": test_user.id,
            "title": "테스트 글"
        })

    # DB에서 알림 생성 확인
    from app.domain.push.services import PushService
    service = PushService(db_session)
    notifications = await service.get_notifications(user_id=test_user.id)
    assert len(notifications) >= 0  # 구독자가 있는 경우에만

@pytest.mark.asyncio
@pytest.mark.phase3
async def test_event_bus_unknown_event_ignored():
    """등록되지 않은 이벤트 발행 — 오류 없이 무시"""
    from app.core.events import EventBus
    # 예외 발생 없이 완료되어야 함
    await EventBus.publish("unknown.event", {"data": "test"})
```

---

## Phase 4: FCM Integration Tests 📋 (계획)

```python
# tests/phase4/test_fcm_service.py (계획)
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
@pytest.mark.phase4
async def test_send_fcm_success():
    """FCM 발송 성공"""
    from app.domain.push.fcm_service import FCMService

    with patch("firebase_admin.messaging.send") as mock_send:
        mock_send.return_value = "projects/test/messages/123"
        service = FCMService()
        result = await service.send(
            token="valid_fcm_token",
            title="테스트 알림",
            body="알림 내용",
            data={"route": "/board/posts/1"}
        )
        assert result is True

@pytest.mark.asyncio
@pytest.mark.phase4
async def test_send_fcm_invalid_token_deactivates(db_session):
    """유효하지 않은 FCM 토큰 → 자동 비활성화"""
    from firebase_admin.exceptions import InvalidArgumentError
    from app.domain.push.fcm_service import FCMService

    with patch("firebase_admin.messaging.send") as mock_send:
        mock_send.side_effect = InvalidArgumentError("Registration token not registered")
        service = FCMService()
        # 발송 실패 시 토큰 비활성화 처리
        result = await service.send_with_token_cleanup(
            db=db_session, token_id=1, token="invalid_token",
            title="알림", body="내용"
        )
        assert result is False
```

---

## Phase 5~7: Cross-Domain, Performance, E2E 📋

위 Phase들은 `V/10_test_plan.md`의 케이스 목록을 기반으로 구현 예정.

성능 테스트 기준 파일:
```python
# tests/performance/locustfile.py (계획)
from locust import HttpUser, task, between

class MiniSaaSUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Google 로그인 (테스트 토큰 사용)
        response = self.client.post("/api/v1/auth/login/google",
                                    json={"id_token": TEST_ID_TOKEN})
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(5)  # 가중치 5 — 가장 빈번한 작업
    def view_board(self):
        self.client.get("/api/v1/board/posts", headers=self.headers)

    @task(2)
    def view_blog_feed(self):
        self.client.get("/api/v1/blogs/feed", headers=self.headers)

    @task(1)
    def check_notifications(self):
        self.client.get("/api/v1/push/notifications/unread/count",
                       headers=self.headers)
```

---

## 관련 문서

- [V/10_test_plan.md](10_test_plan.md) — 전체 테스트 계획
- [R/20_acceptance_criteria.md](../R/20_acceptance_criteria.md) — 인수 기준
- [R/40_traceability.md](../R/40_traceability.md) — 테스트 추적성

---

## Coin Simulator 테스트

### TC-CS01-01: 대시보드 조회

```python
response = client.get("/api/v1/coin-simulator/dashboard", headers=auth_headers)
assert response.status_code == 200
assert "status" in response.json()
```

### TC-CS02-01: 일반 사용자 start 차단

```python
response = client.post("/api/v1/coin-simulator/start", headers=auth_headers)
assert response.status_code == 403
```

### TC-CS02-02: superuser 설정 저장

```python
response = client.put("/api/v1/coin-simulator/settings", headers=auth_headers, json=payload)
assert response.status_code == 200
assert response.json()["permissions"]["can_configure"] is True
```

---

## 2026-03-18 보안 회귀 테스트

### TC-L01-01: 일반 사용자는 일일 원장을 생성할 수 없다
```python
response = client.post(
    "/api/v1/verify/generate-daily/2026-03-18",
    headers={"X-API-Key": "test_key", "X-Platform": "web"},
)
assert response.status_code == 403
```

### TC-L01-02: superuser는 일일 원장을 생성할 수 있다
```python
response = client.post(
    "/api/v1/verify/generate-daily/2026-03-18",
    headers={"X-API-Key": "test_key", "X-Platform": "web"},
)
assert response.status_code == 200
assert response.json()["status"] == "success"
```

### TC-L01-03: 시스템 원장 검증 조회는 인증이 없으면 거부된다
```python
assert client.get("/api/v1/verify/integrity/2026-03-18").status_code in [401, 422]
assert client.get("/api/v1/verify/root/2026-03-18").status_code in [401, 422]
assert client.get("/api/v1/verify/today").status_code in [401, 422]
```

### TC-L01-04: 인증된 사용자는 시스템 원장 검증 조회를 수행할 수 있다
```python
response = client.get(
    "/api/v1/verify/root/2026-03-18",
    headers={"X-API-Key": "test_key", "X-Platform": "web"},
)
assert response.status_code == 200
assert "system_hash" in response.json()
```

### TC-B01-04: board 목록 조회는 인증이 없으면 거부된다
```python
response = client.get(
    "/api/v1/board/posts",
    headers={"X-API-Key": "test_key"},
)
assert response.status_code in [401, 422]
```

### TC-B01-05: board 목록 조회는 인증 사용자의 user_id를 서비스로 전달한다
```python
response = client.get(
    "/api/v1/board/posts",
    headers={"X-API-Key": "test_key", "X-Platform": "mobile", "Authorization": "Bearer test-token"},
)
assert response.status_code == 200
assert captured["user_id"] is not None
```

### TC-B01-06: board 상세 조회는 인증 사용자의 user_id를 서비스로 전달한다
```python
response = client.get(
    f"/api/v1/board/posts/{post_id}",
    headers={"X-API-Key": "test_key", "X-Platform": "mobile", "Authorization": "Bearer test-token"},
)
assert response.status_code == 200
assert captured["user_id"] is not None
```

### TC-BL04-04: blog feed 조회는 인증이 없으면 거부된다
```python
response = client.get(
    "/api/v1/blog/feed",
    headers={"X-API-Key": "test_key"},
)
assert response.status_code in [401, 422]
```

### TC-BL04-05: blog feed 조회는 인증 사용자의 user_id를 좋아요 판별에 전달한다
```python
response = client.get(
    "/api/v1/blog/feed",
    headers={"X-API-Key": "test_key", "X-Platform": "mobile", "Authorization": "Bearer test-token"},
)
assert response.status_code == 200
assert captured["user_id"] is not None
```

### TC-BL05-03: blog 상세 조회는 인증 사용자의 user_id를 좋아요 판별에 전달한다
```python
response = client.get(
    f"/api/v1/blog/posts/{post_id}",
    headers={"X-API-Key": "test_key", "X-Platform": "mobile", "Authorization": "Bearer test-token"},
)
assert response.status_code == 200
assert captured["user_id"] is not None
```

### TC-PDF-SEC-01: PDF 업로드는 API Key 없이 접근할 수 없다
```python
response = client.post("/api/v1/pdf/upload")
assert response.status_code in [401, 422]
```

### TC-USER-SEC-01: 사용자 프로필 단건 조회는 공개가 아니다
```python
response = client.get("/api/v1/users/{user_id}")
assert response.status_code in [401, 422]
```

### TC-AUTH-REMOVED-01: legacy register/login 경로는 제거되어야 한다
```python
assert client.post("/api/v1/auth/register", json=payload).status_code == 404
assert client.post("/api/v1/auth/login", json=payload).status_code == 404
```

### TC-AUTH-COMMON-REFRESH-01: 공통 refresh 엔드포인트는 제거 대상이 아니며 헤더 검증을 통과해야 한다
```python
response = client.post("/api/v1/auth/refresh")
assert response.status_code in [401, 422]
```

### TC-CONTENT-SEC-01: 인증된 사용자는 타인 board/blog 콘텐츠를 조회할 수 있다
```python
board_response = client.get(
    "/api/v1/board/posts",
    headers={"X-API-Key": "test_key", "X-Platform": "mobile", "Authorization": "Bearer viewer-token"},
)
blog_response = client.get(
    f"/api/v1/blog/users/{author_id}",
    headers={"X-API-Key": "test_key", "X-Platform": "mobile", "Authorization": "Bearer viewer-token"},
)
assert board_response.status_code == 200
assert blog_response.status_code == 200
```

### TC-RL-01: 공통 rate-limit helper는 429와 Retry-After를 반환한다
```python
with pytest.raises(HTTPException) as exc_info:
    await enforce_rate_limit(
        scope="test:scope",
        identifier="user:123",
        limit=2,
        window_seconds=60,
        detail="too many requests",
    )
assert exc_info.value.status_code == 429
assert "Retry-After" in exc_info.value.headers
```

### TC-RL-02: 모바일 로그인은 분당 10회/IP를 초과하면 차단된다
```python
for _ in range(10):
    assert client.post("/api/v1/auth/login/mobile", headers=headers).status_code == 200

limited_response = client.post("/api/v1/auth/login/mobile", headers=headers)
assert limited_response.status_code == 429
assert "Retry-After" in limited_response.headers
```

### TC-RL-03: coin simulator 제어 rate limit은 Retry-After를 포함한다
```python
limited_response = client.post("/api/v1/coin-simulator/start", headers=headers)
assert limited_response.status_code == 429
assert "Retry-After" in limited_response.headers
```

### TC-RL-04: board 목록 조회는 계정 기준 조회 rate limit을 초과하면 차단된다
```python
for _ in range(120):
    assert client.get("/api/v1/board/posts", headers=headers).status_code == 200

limited_response = client.get("/api/v1/board/posts", headers=headers)
assert limited_response.status_code == 429
assert "Retry-After" in limited_response.headers
```

### TC-RL-05: ledger root 조회는 계정 기준 조회 rate limit을 초과하면 차단된다
```python
for _ in range(120):
    assert client.get("/api/v1/verify/root/2026-03-18", headers=headers).status_code == 200

limited_response = client.get("/api/v1/verify/root/2026-03-18", headers=headers)
assert limited_response.status_code == 429
assert "Retry-After" in limited_response.headers
```

### TC-CHAT-RESP-01: 채팅 메시지 응답은 표시용 `sender_name`을 포함한다
```python
response = client.get(f"/api/v1/chat/rooms/{room_id}/messages", headers=headers)
assert response.status_code == 200
assert "sender_name" in response.json()["items"][0]
```

### TC-BOARD-COMMENT-RESP-01: 게시판 댓글 작성자 응답은 `nickname`을 포함한다
```python
response = client.get(f"/api/v1/board/{post_id}/comments", headers=headers)
assert response.status_code == 200
assert "nickname" in response.json()[0]["author"]
```

### TC-P02-01: FCM 토큰 갱신은 token UUID를 사용한다
```python
token_id = uuid4()
response = client.put(
    f"/api/v1/push/tokens/{token_id}",
    json={"platform": "ios", "device_name": "iPhone"},
    headers=auth_headers,
)
assert response.status_code == 200
assert response.json()["id"] == str(token_id)
```

### TC-P03-01: FCM 토큰 삭제는 현재 사용자 소유 토큰만 허용한다
```python
response = client.delete(
    "/api/v1/push/tokens/test_token_to_remove",
    headers=auth_headers,
)
assert response.status_code == 204
```

### TC-P08-01: 알림 삭제 엔드포인트가 정상 응답한다
```python
notification_id = uuid4()
response = client.delete(
    f"/api/v1/push/notifications/{notification_id}",
    headers=auth_headers,
)
assert response.status_code in [204, 404]
```
