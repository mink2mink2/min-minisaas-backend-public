# AI/10 — 코딩 규칙 (Python / FastAPI)

이 규칙을 어기는 코드는 작성하지 않는다.

---

## 레이어 규칙

### API Layer (`app/api/v1/endpoints/`)

- HTTP 요청 파싱, Service 호출, 응답 반환만 담당
- 비즈니스 로직 직접 작성 금지
- DB 쿼리 직접 작성 금지 (Service Dependency Injection만)

```python
# ✅ 올바른 API 엔드포인트
@router.post("/posts", response_model=PostResponse, status_code=201)
async def create_post(
    data: PostCreate,
    service: BoardService = Depends(get_board_service),
    current_user: User = Depends(get_current_user),
):
    return await service.create_post(user_id=current_user.id, data=data)

# ❌ 금지: 엔드포인트에서 DB 직접 쿼리
@router.post("/posts")
async def create_post(data: PostCreate, db: AsyncSession = Depends(get_db)):
    post = BoardPost(**data.dict())  # 금지: Service 없이 직접 저장
    db.add(post)
    await db.commit()
```

### Domain Service (`app/domain/*/services.py`)

- 도메인 비즈니스 로직, DB 쿼리, EventBus 발행 담당
- `Request` 객체 직접 참조 금지
- 다른 Domain의 Service를 직접 import 금지 → EventBus 사용

```python
# ✅ Service에서 EventBus 발행
class BoardService:
    async def create_post(self, user_id: int, data: PostCreate) -> PostResponse:
        post = BoardPost(author_id=user_id, **data.dict())
        self.db.add(post)
        await self.db.commit()
        await self.db.refresh(post)

        # 다른 도메인(push)은 이벤트로 통신
        await EventBus.publish("board.post.created", {
            "post_id": post.id,
            "author_id": post.author_id,
            "title": post.title,
        })
        return PostResponse.from_orm(post)

# ❌ 금지: Service에서 다른 도메인 Service 직접 import
from app.domain.push.services import PushService  # 금지!
```

### Core Layer (`app/core/`)

- 기술적 인프라만 제공 (DB, Redis, EventBus, FCM, OAuth 검증)
- 비즈니스 로직 포함 금지

---

## DDD 도메인 경계 규칙

- 각 도메인은 자신의 `models.py`, `schemas.py`, `services.py`만 내부 사용
- 도메인 간 직접 import 금지
- 도메인 간 통신은 반드시 `EventBus.publish()` / `EventBus.subscribe()` 사용

```python
# ✅ 도메인 간 이벤트 통신
# board/services.py
await EventBus.publish("board.post.created", payload)

# push/handlers.py
EventBus.subscribe("board.post.created", handle_new_post_notification)

# ❌ 금지: 도메인 간 직접 호출
from app.domain.push.services import PushService
await push_service.send_notification(...)  # 절대 금지!
```

---

## 비동기(async SQLAlchemy) 규칙

- 모든 DB 쿼리는 `AsyncSession` 사용 (동기 Session 사용 금지)
- `await db.execute(select(...))`, `await db.commit()`, `await db.refresh()` 패턴 사용
- N+1 쿼리 방지: 관계 데이터 조회 시 `selectinload()` 또는 `joinedload()` 사용

```python
# ✅ 올바른 비동기 쿼리
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def get_posts_with_author(db: AsyncSession):
    result = await db.execute(
        select(BoardPost)
        .options(selectinload(BoardPost.author))  # N+1 방지
        .order_by(BoardPost.created_at.desc())
    )
    return result.scalars().all()

# ❌ 금지: 동기 ORM 사용
posts = db.query(BoardPost).all()  # 금지: 동기 쿼리
```

---

## Pydantic v2 스키마 규칙

- API 요청/응답은 반드시 Pydantic v2 스키마 정의
- ORM 모델 직접 반환 금지 → `response_model` 스키마 사용
- ORM → 스키마 변환: `model_config = ConfigDict(from_attributes=True)` 사용

```python
# ✅
class PostResponse(BaseModel):
    id: int
    title: str
    author_id: int

    model_config = ConfigDict(from_attributes=True)

# ❌ ORM 모델 직접 반환
@router.get("/posts")
async def get_posts(db: AsyncSession = Depends(get_db)):
    return await db.execute(select(BoardPost))  # 금지: ORM 객체 직접 반환
```

---

## EventBus 규칙

- 이벤트 이름은 `{domain}.{entity}.{action}` 형식 (예: `board.post.created`)
- 이벤트 핸들러는 `app/domain/{domain}/handlers.py`에만 정의
- 핸들러 등록은 `main.py`의 `startup()` 이벤트에서만

```python
# ✅ 핸들러 등록 위치 (main.py)
@app.on_event("startup")
async def startup():
    register_push_handlers()  # domain/push/handlers.py

# ✅ 핸들러 정의 (domain/push/handlers.py)
def register_push_handlers():
    EventBus.subscribe("board.post.created", handle_new_post_notification)
    EventBus.subscribe("chat.message.received", handle_chat_notification)
```

---

## 환경변수 규칙

- 모든 설정은 `app/core/config.py`의 Pydantic BaseSettings에서 로딩
- 코드에 DB URL, Redis URL, API 키, 비밀번호 하드코딩 절대 금지

```python
# ✅
class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    FIREBASE_CREDENTIALS_PATH: str
    PRODUCTION: bool = False

    model_config = ConfigDict(env_file=".env")

settings = Settings()

# ❌ 하드코딩
DATABASE_URL = "postgresql://user:pass@localhost/db"  # 절대 금지
```

---

## 인증 미들웨어 규칙

- 인증이 필요한 엔드포인트는 `Depends(get_current_user)` 필수
- `get_current_user`는 `app/middleware/auth.py`에서만 정의
- JWT 토큰 검증 로직을 엔드포인트에 직접 작성 금지

```python
# ✅
@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.from_orm(current_user)

# ❌ 엔드포인트에서 직접 토큰 검증
@router.get("/me")
async def get_me(token: str = Header(...)):
    payload = jwt.decode(token, SECRET_KEY, ...)  # 금지: 직접 검증
```

---

## Rate Limiting 규칙

- Rate Limiting은 SlowAPI 기반으로 `app/middleware/rate_limit.py`에서 설정
- 민감한 엔드포인트(로그인, 게시글 작성)에는 반드시 Rate Limit 적용

---

## 오류 처리 규칙

- 비즈니스 예외는 `app/core/exceptions.py`의 커스텀 예외 사용
- `except:` bare except 절대 금지 → 구체적 예외 타입 명시
- 오류 응답 형식은 통일: `{"success": false, "error_code": "...", "message": "..."}`

```python
# ✅
try:
    user = await db.get(User, user_id)
    if not user:
        raise UserNotFoundError(f"User {user_id} not found")
except SQLAlchemyError as e:
    logger.error(f"DB 오류: {e}")
    raise DatabaseError("데이터베이스 오류가 발생했습니다")

# ❌
try:
    ...
except:  # 금지: bare except
    pass
```

---

## 코드 품질 규칙

- Black 포매터, isort, flake8 모두 통과해야 함
- 변경 후 반드시 확인: `make check`
- 민감 정보(비밀번호, API 키, 토큰)를 `logger.info/error()`에 포함 금지

```bash
# ✅ 변경 후 필수 확인
make check    # black, isort, flake8, pylint
pytest tests/ # 전체 테스트 통과
```

---

## 빌드/배포 규칙

- 변경 후 Docker 빌드 확인: `docker compose up -d --build`
- Alembic 마이그레이션 생성 후 반드시 검토: `alembic revision --autogenerate -m "..."`
- Production 배포 전 `make setup` (bootstrap + migrate + verify) 실행
