# AI/00 — 프로젝트 브리프 (Project Brief)

> AI가 이 프로젝트에서 작업을 시작할 때 가장 먼저 읽는 파일이다.
> 프로젝트의 핵심 정보를 한 페이지로 요약한다.

---

## 프로젝트 개요

| 항목 | 내용 |
|------|------|
| **프로젝트명** | MiniSaaS Backend |
| **목적** | Flutter 모바일 앱(Min MiniSaaS)을 위한 REST API 서버 |
| **현재 상태** | 95% 완료 (핵심 기능 구현 완료, 테스트 진행 중) |
| **최종 갱신** | 2026-03-03 |

---

## 기술 스택

| 기술 | 버전 | 역할 |
|------|------|------|
| **Python** | 3.11+ | 런타임 |
| **FastAPI** | 0.100+ | 웹 프레임워크 |
| **PostgreSQL** | 15+ | 주 데이터베이스 |
| **Redis** | 7+ | 캐시 + EventBus |
| **Firebase Admin SDK** | 6.2+ | Google Auth 검증 + FCM 발송 |
| **SQLAlchemy** | 2.0+ | ORM (비동기) |
| **Alembic** | 1.12+ | DB 마이그레이션 |
| **Pydantic** | 2.0+ | 데이터 검증 |
| **httpx** | 0.25+ | 비동기 HTTP (Kakao/Naver OAuth 검증) |

---

## 도메인 구성

| 도메인 | 경로 | 설명 | 상태 |
|--------|------|------|------|
| **auth** | `domain/auth/` | Google/Kakao/Naver 로그인, JWT 발급 | ✅ |
| **chat** | `domain/chat/` | 1:1 채팅방, 실시간 WebSocket, 메시지 이력 | ✅ |
| **board** | `domain/board/` | 게시판 CRUD, 댓글, 좋아요, 북마크, 검색 | ✅ |
| **blog** | `domain/blog/` | 블로그 CRUD, 구독, 피드, 좋아요 | ✅ |
| **push** | `domain/push/` | FCM 토큰 관리, 알림 목록/읽음 처리, FCM 발송 | ✅ |
| **points** | `domain/points/` | 포인트 적립/사용 (기반 구조) | 🔄 |

---

## 주요 패턴

### 1. DDD (Domain-Driven Design)
각 도메인은 `models.py`, `schemas.py`, `services.py`, `handlers.py` 4개 파일로 독립 구성.

### 2. Event-Driven Architecture
도메인 간 통신은 `core/events.py`의 `EventBus`를 통해 이벤트 발행/구독.

```
board.create_post()
  → EventBus.publish("board.post.created", {...})
    → push.handlers.handle_board_post_created()
      → FCM 알림 발송
```

### 3. REST + WebSocket
- REST: 80+ 엔드포인트 (`api/v1/endpoints/`)
- WebSocket: 채팅 실시간 통신 (`WS /api/v1/chat/ws/rooms/{room_id}`)

### 4. 레이어드 아키텍처
```
routes/ (HTTP 계약) → services/ (비즈니스 로직) → models/ (DB)
                          ↑
                    EventBus (도메인 간 이벤트)
```

### 5. 의존성 주입 (FastAPI Depends())
```python
@router.post("/posts")
async def create_post(
    data: PostCreate,
    service: BoardService = Depends(get_board_service),
    current_user: User = Depends(get_current_user),
):
    return await service.create_post(user_id=current_user.id, data=data)
```

---

## 현재 작업 상태

| 태스크 | 상태 | 우선순위 |
|--------|------|---------|
| Phase 3: Event Handler Tests | 📋 시작 전 | 높음 |
| Phase 4: FCM Integration Tests | 📋 시작 전 | 높음 |
| Phase 5: Cross-Domain Tests | 📋 시작 전 | 중간 |
| Phase 6: Performance Tests | 📋 시작 전 | 중간 |
| Phase 7: Flutter E2E Tests | 📋 시작 전 | 낮음 |
| Task 8: Deployment | ⏳ 대기 | 높음 (테스트 완료 후) |

**진행률**: 테스트 41/143 완료 (29%), 전체 프로젝트 95%

---

## 주요 파일 위치

| 파일 | 역할 |
|------|------|
| `app/main.py` | 앱 초기화 |
| `app/core/config.py` | 환경변수 설정 |
| `app/core/events.py` | EventBus |
| `app/core/database.py` | DB 연결 |
| `app/api/v1/router.py` | 라우터 등록 |
| `app/middleware/auth.py` | JWT 인증 |
| `app/middleware/rate_limit.py` | Rate Limiting |
| `migrations/` | Alembic 마이그레이션 |
| `tests/` | pytest 테스트 |

---

## 연관 시스템

| 시스템 | 연결 방식 | 담당 도메인 |
|--------|---------|-----------|
| Flutter 앱 | REST API + WebSocket | 모든 도메인 |
| Firebase Auth | Admin SDK | auth |
| Google FCM | Admin SDK | push |
| Kakao OAuth | HTTP API | auth |
| Naver OAuth | HTTP API | auth |
| GCP Cloud SQL | asyncpg | 모든 도메인 |
| GCP Memorystore | redis-py | core/events, core/cache |

---

## 작업 시작 전 필독

1. [AI/31_rdiv_execution_runbook.md](31_rdiv_execution_runbook.md) — 단계별 작업 절차
2. [D/10_architecture.md](../D/10_architecture.md) — 레이어 구조 및 규칙
3. [AI/20_tasks_queue.md](20_tasks_queue.md) — 현재 작업 큐
