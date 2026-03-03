# D/10 — 시스템 아키텍처

---

## 전체 구조

```
MiniSaaS Backend (FastAPI)
│
├── [HTTP Layer]      api/v1/endpoints/   — HTTP 계약만 담당
├── [Domain Layer]    domain/             — 비즈니스 로직
├── [Core Layer]      core/               — 인프라 (DB, Cache, Auth, FCM)
├── [Middleware]      middleware/         — 횡단 관심사
└── [Entry Point]     main.py             — 앱 초기화만
```

---

## 디렉토리 구조

```
app/
├── core/
│   ├── config.py           # Settings — 환경변수 기반 설정 (Pydantic BaseSettings)
│   ├── database.py         # PostgreSQL + SQLAlchemy AsyncEngine, get_db()
│   ├── cache.py            # Redis 클라이언트, get_cache()
│   ├── events.py           # EventBus — 도메인 이벤트 발행/구독
│   ├── fcm.py              # Firebase Cloud Messaging 초기화 및 발송
│   └── auth/               # OAuth 제공자별 검증 모듈
│       ├── google.py       # Firebase Admin SDK — Google JWT 검증
│       ├── kakao.py        # 카카오 API 서버사이드 검증
│       └── naver.py        # 네이버 API 서버사이드 검증
│
├── domain/
│   ├── auth/
│   │   ├── models.py       # User ORM 모델
│   │   ├── schemas.py      # LoginRequest, LoginResponse, UserResponse
│   │   └── services.py     # AuthService — 로그인, JWT 발급, 사용자 생성
│   │
│   ├── chat/
│   │   ├── models.py       # ChatRoom, ChatParticipant, ChatMessage ORM 모델
│   │   ├── schemas.py      # RoomCreate, MessageCreate, RoomResponse, MessageResponse
│   │   ├── services.py     # ChatService — 채팅방 생성, 메시지 저장, 이력 조회
│   │   └── handlers.py     # EventBus 핸들러 — 채팅 관련 이벤트 수신 처리
│   │
│   ├── board/
│   │   ├── models.py       # BoardPost, BoardComment, BoardReaction ORM 모델
│   │   ├── schemas.py      # PostCreate, PostResponse, CommentCreate, CommentResponse
│   │   ├── services.py     # BoardService — CRUD, 좋아요, 북마크, 검색
│   │   └── handlers.py     # EventBus 핸들러 — 게시글 생성 이벤트 처리
│   │
│   ├── blog/
│   │   ├── models.py       # BlogPost, BlogLike, BlogSubscription ORM 모델
│   │   ├── schemas.py      # BlogCreate, BlogResponse, FeedResponse
│   │   ├── services.py     # BlogService — CRUD, 좋아요, 구독, 피드
│   │   └── handlers.py     # EventBus 핸들러 — 블로그 이벤트 처리
│   │
│   ├── push/
│   │   ├── models.py       # FCMToken, PushNotification ORM 모델
│   │   ├── schemas.py      # TokenCreate, NotificationResponse
│   │   ├── services.py     # PushService — 토큰 CRUD, 알림 목록/읽음 처리
│   │   ├── handlers.py     # EventBus 핸들러 — 다른 도메인 이벤트 수신 → 알림 발송
│   │   └── fcm_service.py  # FCM 실제 발송 로직 분리
│   │
│   └── points/
│       ├── models.py       # UserPoints, PointTransaction ORM 모델
│       ├── schemas.py      # PointResponse, TransactionResponse
│       └── services.py     # PointsService — 적립/사용
│
├── api/
│   └── v1/
│       ├── endpoints/
│       │   ├── auth.py     # POST /login/google|kakao|naver, POST /logout, GET /me
│       │   ├── chat.py     # GET/POST /rooms, GET/POST /rooms/{id}/messages, WS
│       │   ├── board.py    # CRUD /posts, /posts/{id}/like|bookmark|comments
│       │   ├── blog.py     # CRUD /blogs, /feed, /blogs/{id}/like|subscribe
│       │   └── push.py     # CRUD /tokens, CRUD /notifications
│       └── router.py       # APIRouter 집합 — 모든 엔드포인트 등록
│
├── middleware/
│   ├── rate_limit.py       # SlowAPI 기반 Rate Limiting 미들웨어
│   └── auth.py             # JWT 검증 미들웨어 (get_current_user dependency)
│
├── migrations/             # Alembic 마이그레이션 파일
│   └── versions/
│
└── main.py                 # FastAPI 앱 초기화, 미들웨어 등록, 라우터 포함만
```

---

## 레이어 역할 및 규칙

### Layer 1: Core (인프라)

`app/core/`는 **기술적 인프라만 제공**한다. 비즈니스 로직이 없다.

```python
# core/database.py — 데이터베이스 연결 제공
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

engine = create_async_engine(settings.DATABASE_URL, pool_size=20, max_overflow=80)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session

# core/events.py — 이벤트 버스
class EventBus:
    _handlers: dict[str, list[Callable]] = {}

    @classmethod
    def subscribe(cls, event_name: str, handler: Callable):
        cls._handlers.setdefault(event_name, []).append(handler)

    @classmethod
    async def publish(cls, event_name: str, payload: dict):
        for handler in cls._handlers.get(event_name, []):
            await handler(payload)
```

### Layer 2: Domain (비즈니스)

`app/domain/*/`는 **도메인별 비즈니스 로직**을 담는다.

```python
# domain/board/services.py — 비즈니스 로직
class BoardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_post(self, user_id: int, data: PostCreate) -> PostResponse:
        post = BoardPost(author_id=user_id, **data.dict())
        self.db.add(post)
        await self.db.commit()
        await self.db.refresh(post)

        # 이벤트 발행 (push 도메인이 구독)
        await EventBus.publish("board.post.created", {
            "post_id": post.id,
            "author_id": post.author_id,
            "title": post.title,
        })
        return PostResponse.from_orm(post)
```

### Layer 3: API (HTTP 계약)

`app/api/v1/endpoints/`는 **HTTP 요청/응답만 처리**한다. 비즈니스 로직 없음.

```python
# api/v1/endpoints/board.py — HTTP 계약만
@router.post("/posts", response_model=PostResponse, status_code=201)
async def create_post(
    data: PostCreate,
    service: BoardService = Depends(get_board_service),
    current_user: User = Depends(get_current_user),
):
    return await service.create_post(user_id=current_user.id, data=data)
```

### Layer 4: Middleware (횡단 관심사)

`app/middleware/`는 **모든 요청에 공통 적용되는 처리**를 담당한다.

```python
# middleware/auth.py — 인증 의존성
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = verify_jwt_token(token)  # JWT 검증
    user = await db.get(User, payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
```

---

## DDD 원칙

### 도메인 경계 (Bounded Context)

각 도메인은 독립된 경계를 가진다:

| 도메인 | 책임 | 외부 의존 방식 |
|--------|------|--------------|
| auth | 인증, 사용자 관리 | 없음 (Core만 사용) |
| chat | 채팅방, 실시간 메시지 | EventBus 발행 |
| board | 게시판 CRUD | EventBus 발행 |
| blog | 블로그 CRUD, 구독 | EventBus 발행 |
| push | FCM 알림 관리 | EventBus 구독 (다른 도메인 이벤트 수신) |
| points | 포인트 적립/사용 | EventBus 구독 |

### 이벤트 목록

| 이벤트 이름 | 발행 도메인 | 구독 도메인 | 설명 |
|------------|-----------|-----------|------|
| `board.post.created` | board | push | 새 게시글 알림 |
| `board.comment.created` | board | push | 댓글 알림 |
| `blog.post.created` | blog | push | 새 블로그 글 구독자 알림 |
| `chat.message.received` | chat | push | 채팅 오프라인 알림 |
| `auth.user.registered` | auth | points | 신규 가입 보너스 포인트 |

---

## 기술 스택

| 기술 | 버전 | 용도 |
|------|------|------|
| Python | 3.11+ | 런타임 |
| FastAPI | 0.100+ | 웹 프레임워크 |
| SQLAlchemy | 2.0+ | ORM (비동기) |
| Alembic | 1.12+ | DB 마이그레이션 |
| asyncpg | 0.28+ | PostgreSQL 비동기 드라이버 |
| redis-py | 5.0+ | Redis 클라이언트 |
| firebase-admin | 6.2+ | Google Auth + FCM |
| httpx | 0.25+ | 비동기 HTTP 클라이언트 (OAuth 검증) |
| pydantic | 2.0+ | 데이터 검증 및 스키마 |
| python-jose | 3.3+ | JWT 생성/검증 |
| slowapi | 0.1+ | Rate Limiting |

---

## 앱 초기화 흐름 (main.py)

```python
# main.py — 초기화만 담당, 로직 없음
from fastapi import FastAPI
from app.core.database import init_db
from app.core.cache import init_cache
from app.core.fcm import init_fcm
from app.api.v1.router import api_router
from app.middleware.rate_limit import setup_rate_limit
from app.domain.push.handlers import register_push_handlers

app = FastAPI(
    title="MiniSaaS API",
    docs_url=None if settings.PRODUCTION else "/docs",  # Production에서 비활성화
    redoc_url=None if settings.PRODUCTION else "/redoc",
)

@app.on_event("startup")
async def startup():
    await init_db()
    await init_cache()
    await init_fcm()
    register_push_handlers()  # EventBus 핸들러 등록

setup_rate_limit(app)
app.include_router(api_router, prefix="/api/v1")
```

---

## 관련 문서

- [D/20_data_model.md](20_data_model.md) — DB 스키마 상세
- [D/30_api_contract.md](30_api_contract.md) — API 엔드포인트 전체 목록
- [D/90_decisions.md](90_decisions.md) — 아키텍처 결정 기록
- [AI/10_coding_rules.md](../AI/10_coding_rules.md) — AI 코딩 규칙
