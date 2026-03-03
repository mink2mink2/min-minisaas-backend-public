# MiniSaaS Backend 문서

> **문서는 백엔드 유지보수를 위한 실행 기준이다.**
>
> 이 문서 없이 코드를 수정하거나 기능을 추가하지 말 것. 모든 변경은 문서와 동기화되어야 한다.

---

## Start Here

**AI 또는 신규 개발자라면 반드시 이 파일을 먼저 읽어라.**

작업 시작 전 항상 다음 Runbook을 따른다:

- [AI/31_rdiv_execution_runbook.md](AI/31_rdiv_execution_runbook.md) — 작업 실행 단계별 가이드 (필독)

---

## 문서 구조

| 폴더 | 목적 |
|------|------|
| `R/` | Requirements — 요구사항, 유저 스토리, 인수 기준, 비기능 요구사항 |
| `D/` | Design — 아키텍처, 데이터 모델, API 계약, 아키텍처 결정 기록 |
| `I/` | Implementation — 구현 계획, 변경 이력, 배포 가이드 |
| `V/` | Verification — 테스트 계획, 테스트 케이스, 보안 검토, 관찰성 |
| `AI/` | AI Context — 프로젝트 브리프, 코딩 규칙, 작업 큐, 컨텍스트 팩 |

---

## Default Instruction for AI

AI가 이 프로젝트에서 작업할 때 반드시 지켜야 할 기본 지침이다.

1. **작업 시작 전** `AI/31_rdiv_execution_runbook.md`를 읽고 단계별로 따른다.
2. **코드 작성 전** `D/10_architecture.md`의 레이어 구조를 확인한다.
3. **API 변경 시** `D/30_api_contract.md`를 먼저 갱신하고 코드를 수정한다.
4. **보안 관련 변경 시** `V/30_security_review.md` 체크리스트를 확인한다.
5. **완료 전** 아래 DoD(Definition of Done) 기준을 모두 충족한다.

## Prompt Example

새 대화(창)를 열고 AI에게 작업을 시킬 때 아래 문장을 그대로 붙여넣는다:

```
README.md를 먼저 읽고, README에 적힌 Start Here/Default Instruction대로 /docs/AI/31_rdiv_execution_runbook.md 기준으로 문서+코드+검증까지 완료해.
```

---

## Definition of Done (DoD)

작업이 완료되었다고 판단하려면 다음 기준을 모두 충족해야 한다:

- [ ] **R/D/I/V 동시 갱신**: 변경사항에 해당하는 R, D, I, V 문서를 모두 갱신했다
- [ ] **API 계약 변경 기록**: API 엔드포인트가 추가/변경/삭제된 경우 `D/90_decisions.md`에 결정 근거를 기록했다
- [ ] **테스트 결과 없이 완료 처리 금지**: 새로운 기능은 반드시 테스트 케이스가 작성되고 통과되어야 완료로 처리한다
- [ ] **앱 연동 영향 갱신**: 앱(Flutter)과의 연동에 영향이 있는 변경이면 `D/30_api_contract.md`와 `R/40_traceability.md`를 함께 갱신한다
- [ ] **보안 검토 통과**: `V/30_security_review.md` 체크리스트의 해당 항목을 확인했다
- [ ] **변경 이력 기록**: `I/20_change_log.md`에 날짜와 함께 변경 내용을 기록했다

---

## Architecture Rules (AI 필독 ⚠️)

이 규칙들은 **코드베이스 일관성을 위한 강제 사항**이다. 예외 없이 따른다.

### 레이어 역할 분리

| 레이어 | 위치 | 담당 역할 | 금지 사항 |
|--------|------|-----------|-----------|
| **Routes** | `api/v1/endpoints/` | HTTP 요청/응답 파싱, 의존성 주입 호출 | 비즈니스 로직 직접 작성 금지 |
| **Middleware** | `middleware/` | 인증, Rate Limiting 등 횡단 관심사 | 도메인 로직 포함 금지 |
| **Services** | `domain/*/services.py` | 도메인 로직, 응답 데이터 조립 | HTTP 요청 객체 직접 참조 금지 |
| **Domain** | `domain/*/` | 모델, 스키마, 서비스, 이벤트 핸들러 | 다른 도메인 서비스 직접 임포트 금지 |

#### routes/ 규칙
`routes/`(= `api/v1/endpoints/`)는 **HTTP 계약 레이어만 담당**한다.
- 요청 파라미터 파싱 및 검증 (Pydantic 스키마 활용)
- 서비스 레이어 호출 (`Depends()`로 주입된 서비스 사용)
- HTTP 응답 반환
- **비즈니스 로직을 직접 작성하는 것은 엄격히 금지**

```python
# ✅ 올바른 패턴
@router.post("/posts", response_model=PostResponse)
async def create_post(
    data: PostCreate,
    service: BoardService = Depends(get_board_service),
    current_user: User = Depends(get_current_user),
):
    return await service.create_post(user_id=current_user.id, data=data)

# ❌ 금지 패턴 — 비즈니스 로직이 라우터에 있음
@router.post("/posts")
async def create_post(data: PostCreate, db: AsyncSession = Depends(get_db)):
    post = BoardPost(**data.dict(), author_id=current_user.id)
    db.add(post)
    await db.commit()
    return post
```

#### middleware/ 규칙
`middleware/`는 **횡단 관심사(Cross-cutting concerns)를 독립 모듈로 분리**한다.
- 인증 미들웨어: JWT 검증, 사용자 컨텍스트 설정
- Rate Limiting 미들웨어: 엔드포인트별 요청 빈도 제한
- 각 미들웨어는 단일 책임을 가진 독립 파일로 관리한다

#### services/ 규칙
`domain/*/services.py`는 **도메인 로직과 응답 조립만 담당**한다.
- 데이터베이스 쿼리 실행
- 비즈니스 규칙 적용
- 이벤트 발행 (`EventBus.publish()`)
- 다른 도메인과의 통신은 EventBus를 통해 간접적으로 처리

#### domain/ 규칙
각 도메인은 **독립된 파일로 분리**한다.
- `models.py`: SQLAlchemy ORM 모델
- `schemas.py`: Pydantic 요청/응답 스키마
- `services.py`: 비즈니스 로직
- `handlers.py`: EventBus 이벤트 핸들러

---

## 모듈 독립화 원칙

- **도메인 간 직접 의존 금지**: `domain/board/services.py`에서 `domain/blog/services.py`를 직접 임포트하지 않는다
- **이벤트를 통한 통신**: 도메인 간 통신은 반드시 `core/events.py`의 `EventBus`를 통해 처리한다
- **공유 유틸리티**: `core/`에만 위치한다
- **신규 도메인 추가 시**: 기존 도메인을 수정하지 않고 새 도메인 디렉토리를 추가한다

---

## 이벤트 드리븐 / 의존성 주입 원칙

### 이벤트 발행 패턴
```python
# services.py에서 이벤트 발행
from app.core.events import EventBus

class BoardService:
    async def create_post(self, user_id: int, data: PostCreate) -> PostResponse:
        post = await self._create_in_db(user_id, data)
        # 이벤트 발행 — push 도메인이 구독하여 알림 처리
        await EventBus.publish("board.post.created", {
            "post_id": post.id,
            "author_id": post.author_id,
            "title": post.title,
        })
        return PostResponse.from_orm(post)
```

### 의존성 주입 패턴 (FastAPI Depends() 활용)
```python
# 의존성 정의
async def get_board_service(db: AsyncSession = Depends(get_db)) -> BoardService:
    return BoardService(db)

# 라우터에서 사용
@router.get("/posts")
async def list_posts(service: BoardService = Depends(get_board_service)):
    return await service.list_posts()
```

---

## 보안 항상 주의

보안 관련 변경 시 반드시 [V/30_security_review.md](V/30_security_review.md) 체크리스트를 확인한다.

주요 보안 원칙:
- 모든 엔드포인트에 인증 적용 (공개 엔드포인트 명시적 예외 처리)
- 민감정보(토큰, DB URL 등)를 로그에 출력하지 않는다
- Rate Limiting을 공개 엔드포인트에 반드시 적용한다
- Production 환경에서 `/docs`, `/redoc`를 비활성화한다

---

## 빠른 링크

| 문서 | 용도 |
|------|------|
| [R/00_overview.md](R/00_overview.md) | 프로젝트 개요 |
| [R/10_user_stories.md](R/10_user_stories.md) | 유저 스토리 |
| [D/10_architecture.md](D/10_architecture.md) | 아키텍처 구조 |
| [D/30_api_contract.md](D/30_api_contract.md) | API 엔드포인트 전체 목록 |
| [D/90_decisions.md](D/90_decisions.md) | 아키텍처 결정 기록 (ADR) |
| [I/10_implementation_plan.md](I/10_implementation_plan.md) | 구현 현황 |
| [V/10_test_plan.md](V/10_test_plan.md) | 테스트 계획 |
| [V/30_security_review.md](V/30_security_review.md) | 보안 체크리스트 |
| [AI/31_rdiv_execution_runbook.md](AI/31_rdiv_execution_runbook.md) | AI 작업 Runbook |
