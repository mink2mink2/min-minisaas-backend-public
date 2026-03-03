# AI/10 — 코딩 규칙 (Coding Rules for AI)

> 이 규칙들은 선택 사항이 아니다. 코드를 작성하기 전에 반드시 읽고 따른다.

---

## 작업 시작 전 필수 확인

1. `D/10_architecture.md`의 레이어 구조를 확인한다 — 내 변경사항이 어느 레이어인지 파악
2. `AI/20_tasks_queue.md`에서 현재 우선순위 태스크를 확인한다
3. `D/30_api_contract.md`에서 기존 API 계약을 확인한다 (중복 엔드포인트 추가 방지)

---

## Rule 1: 레이어 역할 절대 준수

### routes/에 비즈니스 로직 작성 금지

`api/v1/endpoints/` 파일은 **HTTP 계약만 담당**한다.

```python
# ✅ 올바른 패턴 — 서비스 호출만 함
@router.post("/posts", response_model=PostResponse, status_code=201)
async def create_post(
    data: PostCreate,
    service: BoardService = Depends(get_board_service),
    current_user: User = Depends(get_current_user),
):
    return await service.create_post(user_id=current_user.id, data=data)

# ❌ 금지 패턴 — DB 쿼리가 라우터에 있음
@router.post("/posts")
async def create_post(data: PostCreate, db: AsyncSession = Depends(get_db)):
    post = BoardPost(**data.dict())
    db.add(post)
    await db.commit()
    return post
```

### middleware/에서만 횡단 관심사 처리

- 인증 (`get_current_user`): `middleware/auth.py`
- Rate Limiting: `middleware/rate_limit.py`
- 새 횡단 관심사(로깅 미들웨어, 요청 ID 등)는 `middleware/` 신규 파일로 분리

```python
# ✅ 올바른 패턴 — middleware/auth.py에 인증 로직
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = verify_jwt_token(token)
    user = await db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ❌ 금지 패턴 — 인증 로직이 라우터에 있음
@router.get("/posts")
async def list_posts(token: str = Header(None)):
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])  # 라우터에서 직접
    ...
```

---

## Rule 2: FastAPI Depends()로 의존성 주입

모든 의존성(DB, Service, 현재 사용자)은 `Depends()`를 통해 주입한다.

```python
# ✅ 의존성 정의 패턴
async def get_board_service(db: AsyncSession = Depends(get_db)) -> BoardService:
    return BoardService(db)

# ✅ 사용 패턴
@router.get("/posts")
async def list_posts(
    service: BoardService = Depends(get_board_service),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 20,
):
    return await service.list_posts(skip=skip, limit=limit)
```

---

## Rule 3: 도메인 간 직접 임포트 금지

도메인 간 통신은 **반드시 EventBus를 통해** 처리한다.

```python
# ✅ 올바른 패턴 — EventBus로 간접 통신
# domain/board/services.py
from app.core.events import EventBus

class BoardService:
    async def create_post(self, ...):
        post = await self._create_in_db(...)
        await EventBus.publish("board.post.created", {
            "post_id": post.id,
            "author_id": post.author_id,
        })
        return post

# domain/push/handlers.py (EventBus 핸들러)
async def handle_board_post_created(payload: dict):
    # push 도메인에서 직접 구독하여 처리
    await push_service.create_notification(...)

# ❌ 금지 패턴 — 도메인 간 직접 임포트
# domain/board/services.py
from app.domain.push.services import PushService  # 절대 금지!

class BoardService:
    async def create_post(self, ...):
        post = await self._create_in_db(...)
        push_service = PushService(self.db)
        await push_service.create_notification(...)  # 강결합!
```

---

## Rule 4: 이벤트 발행 패턴

```python
# 이벤트 발행 표준 패턴
from app.core.events import EventBus

await EventBus.publish("domain.entity.action", {
    "entity_id": entity.id,
    "actor_id": user.id,
    # 핸들러에서 필요한 최소 정보만 포함
})

# 이벤트 이름 규칙: "domain.entity.action"
# 예시:
# "board.post.created"
# "board.comment.created"
# "blog.post.created"
# "chat.message.received"
# "auth.user.registered"
```

---

## Rule 5: 새 기능 추가 절차

### 새 도메인 추가 시

1. `domain/new_domain/` 디렉토리 생성
2. `models.py` → `schemas.py` → `services.py` → `handlers.py` 순서로 작성
3. `api/v1/endpoints/new_domain.py` 작성 (라우터만)
4. `api/v1/router.py`에 라우터 등록
5. Alembic 마이그레이션 생성 및 실행
6. `core/events.py`에 필요한 이벤트 핸들러 등록
7. `D/10_architecture.md` 업데이트
8. `D/20_data_model.md` 업데이트
9. `D/30_api_contract.md` 업데이트

### 새 엔드포인트 추가 시

1. `D/30_api_contract.md`에 먼저 API 명세 작성
2. `domain/*/services.py`에 비즈니스 로직 추가
3. `api/v1/endpoints/*.py`에 라우터 핸들러 추가 (로직 없이 서비스 호출만)
4. 테스트 케이스 작성 (Phase 2 패턴 참고)
5. `R/40_traceability.md` 업데이트
6. `I/20_change_log.md`에 변경 기록

---

## Rule 6: 타입 힌트 필수

모든 함수에 입력/출력 타입 힌트를 작성한다.

```python
# ✅ 올바른 패턴
async def create_post(
    self,
    user_id: int,
    data: PostCreate,
) -> PostResponse:
    ...

# ❌ 금지 패턴
async def create_post(self, user_id, data):
    ...
```

---

## Rule 7: 에러 처리 패턴

```python
# ✅ 표준 에러 처리 패턴
from fastapi import HTTPException

class BoardService:
    async def get_post(self, post_id: int) -> BoardPost:
        post = await self.db.get(BoardPost, post_id)
        if not post or post.is_deleted:
            raise HTTPException(status_code=404, detail="Post not found")
        return post

    async def update_post(self, user_id: int, post_id: int, data: PostUpdate) -> PostResponse:
        post = await self.get_post(post_id)
        if post.author_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this post")
        # 수정 로직...
```

---

## Rule 8: 테스트 없이 PR 금지

- 새 서비스 메서드: Phase 1 패턴의 단위 테스트 작성
- 새 엔드포인트: Phase 2 패턴의 API 테스트 작성
- 테스트가 통과하지 않으면 완료로 처리하지 않는다

```bash
# 테스트 실행 확인
pytest tests/ -v -x --asyncio-mode=auto
# 모든 테스트 통과 확인 후 PR
```

---

## Rule 9: V/30_security_review.md 체크 후 PR

보안 관련 사항이 있는 경우 반드시 체크리스트를 확인한다:
- 새 공개 엔드포인트 추가 시
- 인증 로직 변경 시
- DB 쿼리 변경 시
- 외부 API 연동 추가 시

---

## Rule 10: 코드 스타일

```bash
# 커밋 전 실행
black app/ tests/       # 코드 포맷팅
isort app/ tests/       # import 정렬
ruff check app/ tests/  # 린터 검사

# 또는 pre-commit hook
pre-commit run --all-files
```

### 네이밍 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| 파일명 | snake_case | `board_service.py` |
| 클래스명 | PascalCase | `BoardService`, `PostCreate` |
| 함수/변수 | snake_case | `create_post`, `user_id` |
| 상수 | UPPER_SNAKE | `MAX_CONTENT_LENGTH` |
| 이벤트 이름 | `domain.entity.action` | `board.post.created` |
| API 엔드포인트 | `/resource/{id}/action` | `/board/posts/{id}/like` |

---

## 빠른 참조

| 질문 | 참조 문서 |
|------|---------|
| "이게 어느 레이어인가?" | [D/10_architecture.md](../D/10_architecture.md) |
| "이 API 이미 있나?" | [D/30_api_contract.md](../D/30_api_contract.md) |
| "테스트는 어떻게 작성하나?" | [V/20_test_cases.md](../V/20_test_cases.md) |
| "보안 체크는?" | [V/30_security_review.md](../V/30_security_review.md) |
| "DB 스키마는?" | [D/20_data_model.md](../D/20_data_model.md) |
| "컨텍스트 팩" | [AI/30_context_pack.md](30_context_pack.md) |
