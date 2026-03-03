# AI/30 — 컨텍스트 팩 (Context Pack)

> 새 대화 시작 시 AI가 빠르게 컨텍스트를 파악하기 위한 요약본.
> 상세 내용은 각 섹션에 링크된 문서 참고.

---

## 프로젝트 한 줄 요약

**MiniSaaS Backend** — FastAPI 기반 SaaS 플랫폼 API 서버.
Chat, Board, Blog, Push Notification, OAuth 인증을 제공한다.

---

## 현재 상태 (2026-03-03)

- 전체 완성도: **~95%**
- 코드 라인: **~5,220줄**
- 테스트: **41/143 완료 (29%)**
- 배포: **미완료 (Task 8 대기)**

---

## 기술 스택

```
FastAPI 0.100+ + PostgreSQL + Redis + Firebase Admin SDK
SQLAlchemy 2.0 (비동기) + Alembic + pytest-asyncio
```

---

## 디렉토리 핵심 파일

```
app/
├── main.py                     # 앱 초기화 진입점
├── core/
│   ├── config.py               # 환경변수 설정 (Settings)
│   ├── database.py             # DB 세션 (get_db dependency)
│   ├── cache.py                # Redis 클라이언트 (get_cache dependency)
│   ├── events.py               # EventBus.publish() / EventBus.subscribe()
│   └── auth/                   # OAuth 검증 (google/kakao/naver)
├── domain/
│   ├── {domain}/models.py      # ORM 모델
│   ├── {domain}/schemas.py     # Pydantic 스키마
│   ├── {domain}/services.py    # 비즈니스 로직
│   └── push/handlers.py        # EventBus 핸들러 등록
├── api/v1/endpoints/
│   └── {domain}.py             # HTTP 라우터 (Depends() 활용)
└── middleware/
    ├── rate_limit.py            # SlowAPI Rate Limiting
    └── auth.py                  # get_current_user dependency
```

---

## 도메인별 API 엔드포인트 요약

| 도메인 | 엔드포인트 접두사 | 주요 기능 |
|--------|----------------|---------|
| auth | `/api/v1/auth/` | Google/Kakao/Naver 로그인, JWT |
| chat | `/api/v1/chat/` | 채팅방 CRUD, WebSocket, 메시지 |
| board | `/api/v1/board/` | 게시글 CRUD, 댓글, 좋아요, 북마크 |
| blog | `/api/v1/blogs/` | 블로그 CRUD, 피드, 구독, 좋아요 |
| push | `/api/v1/push/` | FCM 토큰, 알림 목록/읽음 |

전체 계약: [D/30_api_contract.md](../D/30_api_contract.md)

---

## 핵심 패턴

### 1. 새 엔드포인트 추가

```python
# 1. api/v1/endpoints/{domain}.py에 라우터 추가
@router.get("/items", response_model=list[ItemResponse])
async def list_items(
    service: ItemService = Depends(get_item_service),
    current_user: User = Depends(get_current_user),
):
    return await service.list(user_id=current_user.id)

# 2. domain/{domain}/services.py에 비즈니스 로직 추가
class ItemService:
    async def list(self, user_id: int) -> list[Item]:
        ...

# 3. D/30_api_contract.md 갱신
# 4. V/20_test_cases.md에 테스트 케이스 추가
```

### 2. 이벤트 발행/구독

```python
# 발행 (다른 도메인에서)
await EventBus.publish("board.post.created", {
    "post_id": post.id,
    "author_id": post.author_id,
})

# 구독 (push/handlers.py에서)
@EventBus.handler("board.post.created")
async def on_post_created(payload: dict):
    await push_service.notify_followers(payload["author_id"])
```

### 3. 의존성 주입

```python
# DB 세션
async def get_board_service(db: AsyncSession = Depends(get_db)) -> BoardService:
    return BoardService(db=db)

# 인증
async def protected_endpoint(
    current_user: User = Depends(get_current_user)
):
    ...
```

---

## 이벤트 목록

| 이벤트 이름 | 발행 위치 | 구독 위치 |
|------------|---------|---------|
| `board.post.created` | `domain/board/services.py` | `domain/push/handlers.py` |
| `board.comment.created` | `domain/board/services.py` | `domain/push/handlers.py` |
| `blog.post.created` | `domain/blog/services.py` | `domain/push/handlers.py` |
| `chat.message.received` | `domain/chat/services.py` | `domain/push/handlers.py` |
| `auth.user.registered` | `domain/auth/services.py` | `domain/points/handlers.py` |

---

## 환경변수 목록

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/minisaas

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# Firebase
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-service-account.json

# OAuth
KAKAO_REST_API_KEY=xxx
NAVER_CLIENT_ID=xxx
NAVER_CLIENT_SECRET=xxx

# App
ENVIRONMENT=development  # production으로 변경 시 /docs 비활성화
```

---

## 테스트 실행 방법

```bash
# 전체 테스트
pytest tests/ -v

# 특정 도메인 테스트
pytest tests/domain/push/ -v

# 커버리지 포함
pytest --cov=app --cov-report=html

# 빠른 단위 테스트만
pytest tests/unit/ -v --timeout=30
```

---

## 관련 문서 링크

| 목적 | 문서 |
|------|------|
| 아키텍처 레이어 규칙 | [D/10_architecture.md](../D/10_architecture.md) |
| DB 스키마 | [D/20_data_model.md](../D/20_data_model.md) |
| API 계약 전체 | [D/30_api_contract.md](../D/30_api_contract.md) |
| 코딩 규칙 | [AI/10_coding_rules.md](10_coding_rules.md) |
| 보안 체크리스트 | [V/30_security_review.md](../V/30_security_review.md) |
| 테스트 계획 | [V/10_test_plan.md](../V/10_test_plan.md) |
| 배포 가이드 | [I/30_deploy_guide.md](../I/30_deploy_guide.md) |
| 태스크 큐 | [AI/20_tasks_queue.md](20_tasks_queue.md) |
