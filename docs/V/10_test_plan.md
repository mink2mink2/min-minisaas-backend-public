# V/10 — 테스트 계획 (Test Plan)

> 총 143개 테스트 케이스 계획 (현재 41/143 완료)
> 최종 갱신: 2026-03-03

---

## 테스트 전략

### 테스트 피라미드

```
         /\
        /  \          E2E Tests (Flutter)
       /    \         Phase 7: 10 tests
      /------\
     /        \       Integration Tests
    /          \      Phase 3-6: 43 tests
   /------------\
  /              \    Unit Tests (Service + API)
 /                \   Phase 1-2: 41 tests ✅
/------------------\
```

### 테스트 프레임워크

| 도구 | 용도 |
|------|------|
| `pytest` | 테스트 러너 |
| `pytest-asyncio` | 비동기 테스트 지원 |
| `httpx` | 비동기 HTTP 클라이언트 (API 테스트) |
| `pytest-mock` | Mock 객체 생성 |
| `asyncpg` | 테스트용 PostgreSQL 연결 |
| `fakeredis` | Redis Mock |
| `locust` | 성능 테스트 (Phase 6) |

### 테스트 환경

```bash
# 테스트 환경 설정
export TEST_DATABASE_URL=postgresql+asyncpg://test:test@localhost/test_db
export TEST_REDIS_URL=redis://localhost:6379/1

# 전체 테스트 실행
pytest tests/ -v --asyncio-mode=auto

# 특정 Phase만 실행
pytest tests/ -v -m "phase1"
pytest tests/ -v -m "phase2"

# 커버리지 측정
pytest tests/ --cov=app --cov-report=html
```

---

## Phase 1: Service Unit Tests ✅ (20/20)

**대상**: `domain/*/services.py` 단위 테스트
**완료일**: 2026-03-02

| # | 테스트 케이스 | 도메인 | 상태 |
|---|-------------|--------|------|
| 1 | AuthService.create_or_get_user — 신규 사용자 생성 | auth | ✅ |
| 2 | AuthService.create_or_get_user — 기존 사용자 반환 | auth | ✅ |
| 3 | AuthService.create_jwt — 유효한 JWT 생성 | auth | ✅ |
| 4 | AuthService.verify_jwt — 유효한 토큰 검증 | auth | ✅ |
| 5 | AuthService.verify_jwt — 만료된 토큰 거부 | auth | ✅ |
| 6 | ChatService.get_or_create_room — 신규 채팅방 생성 | chat | ✅ |
| 7 | ChatService.get_or_create_room — 기존 채팅방 반환 | chat | ✅ |
| 8 | ChatService.save_message — 메시지 DB 저장 | chat | ✅ |
| 9 | BoardService.create_post — 게시글 생성 및 이벤트 발행 | board | ✅ |
| 10 | BoardService.create_post — Rate Limit 초과 시 거부 | board | ✅ |
| 11 | BoardService.add_like — 좋아요 추가 및 카운트 증가 | board | ✅ |
| 12 | BoardService.add_like — 중복 좋아요 예외 | board | ✅ |
| 13 | BoardService.remove_like — 좋아요 취소 및 카운트 감소 | board | ✅ |
| 14 | BlogService.create_post — 블로그 글 생성 및 slug 생성 | blog | ✅ |
| 15 | BlogService.create_post — slug 중복 시 자동 번호 부여 | blog | ✅ |
| 16 | BlogService.get_feed — 구독 블로거의 글만 반환 | blog | ✅ |
| 17 | PushService.register_token — 신규 토큰 등록 | push | ✅ |
| 18 | PushService.register_token — 기존 토큰 갱신 | push | ✅ |
| 19 | PushService.mark_as_read — 읽음 처리 | push | ✅ |
| 20 | PushService.get_unread_count — 읽지 않은 수 반환 | push | ✅ |

---

## Phase 2: API Endpoint Tests ✅ (21/21)

**대상**: `api/v1/endpoints/` HTTP 엔드포인트 테스트
**완료일**: 2026-03-03

| # | 테스트 케이스 | 엔드포인트 | 상태 |
|---|-------------|----------|------|
| 1 | Google 로그인 — 유효한 토큰 | POST /auth/login/google | ✅ |
| 2 | Google 로그인 — 유효하지 않은 토큰 (401) | POST /auth/login/google | ✅ |
| 3 | 내 정보 조회 — 인증됨 | GET /auth/me | ✅ |
| 4 | 내 정보 조회 — 비인증 (401) | GET /auth/me | ✅ |
| 5 | 채팅방 생성 | POST /chat/rooms | ✅ |
| 6 | 채팅방 목록 조회 | GET /chat/rooms | ✅ |
| 7 | 메시지 이력 조회 | GET /chat/rooms/{id}/messages | ✅ |
| 8 | 메시지 이력 — 비참여자 접근 (403) | GET /chat/rooms/{id}/messages | ✅ |
| 9 | 게시글 목록 조회 (비인증) | GET /board/posts | ✅ |
| 10 | 게시글 작성 (인증) | POST /board/posts | ✅ |
| 11 | 게시글 작성 (비인증 401) | POST /board/posts | ✅ |
| 12 | 게시글 수정 (본인) | PUT /board/posts/{id} | ✅ |
| 13 | 게시글 수정 (타인 403) | PUT /board/posts/{id} | ✅ |
| 14 | 게시글 삭제 | DELETE /board/posts/{id} | ✅ |
| 15 | 좋아요 추가/취소 | POST/DELETE /board/posts/{id}/like | ✅ |
| 16 | 블로그 글 작성 | POST /blogs | ✅ |
| 17 | 블로그 피드 조회 | GET /blogs/feed | ✅ |
| 18 | FCM 토큰 등록 | POST /push/tokens | ✅ |
| 19 | 알림 목록 조회 | GET /push/notifications | ✅ |
| 20 | 알림 읽음 처리 | PUT /push/notifications/{id}/read | ✅ |
| 21 | 전체 읽음 처리 | PUT /push/notifications/read-all | ✅ |

---

## Phase 3: Event Handler Tests 📋 (0/10)

**대상**: `domain/*/handlers.py` EventBus 핸들러 테스트
**예정**: 2026-03-05 ~ 2026-03-07

| # | 테스트 케이스 | 핸들러 | 상태 |
|---|-------------|--------|------|
| 22 | board.post.created 이벤트 발행 시 PushHandler 호출 | push.handlers | 📋 |
| 23 | board.comment.created 이벤트 → 게시글 작성자에게 알림 저장 | push.handlers | 📋 |
| 24 | blog.post.created → 구독자 목록 조회 및 알림 저장 | push.handlers | 📋 |
| 25 | chat.message.received → 오프라인 사용자 알림 저장 | push.handlers | 📋 |
| 26 | EventBus.subscribe / publish 동작 검증 | core.events | 📋 |
| 27 | 핸들러 미등록 이벤트 발행 시 오류 없이 무시 | core.events | 📋 |
| 28 | board.post.created — 구독자 없을 때 알림 미발송 | push.handlers | 📋 |
| 29 | blog.post.created — 자기 자신 구독 제외 | push.handlers | 📋 |
| 30 | auth.user.registered → points 핸들러 (신규 가입 보너스) | points.handlers | 📋 |
| 31 | 이벤트 핸들러 예외 발생 시 다른 핸들러 영향 없음 | core.events | 📋 |

---

## Phase 4: FCM Integration Tests 📋 (0/10)

**대상**: `domain/push/fcm_service.py` FCM 실제 발송 테스트 (Mock 사용)
**예정**: 2026-03-08 ~ 2026-03-10

| # | 테스트 케이스 | 상태 |
|---|-------------|------|
| 32 | 단일 FCM 토큰 발송 성공 | 📋 |
| 33 | 여러 FCM 토큰 일괄 발송 | 📋 |
| 34 | 유효하지 않은 FCM 토큰 → 자동 비활성화 | 📋 |
| 35 | FCM API 타임아웃 처리 | 📋 |
| 36 | FCM 발송 실패 시 알림 DB 저장 여부 | 📋 |
| 37 | 비활성 토큰으로 발송 안 함 | 📋 |
| 38 | iOS 토큰 vs Android 토큰 처리 차이 | 📋 |
| 39 | FCM Dry-run 모드 테스트 | 📋 |
| 40 | 알림 `data` 페이로드 정확성 검증 | 📋 |
| 41 | FCM 서비스 초기화 실패 시 앱 시작 실패 처리 | 📋 |

---

## Phase 5: Cross-Domain Tests 📋 (0/15)

**대상**: 도메인 간 이벤트 흐름 종단 간 테스트
**예정**: 2026-03-11 ~ 2026-03-13

| # | 테스트 시나리오 | 상태 |
|---|--------------|------|
| 42 | 게시글 작성 → 이벤트 발행 → 알림 DB 저장 → FCM 발송 | 📋 |
| 43 | 댓글 작성 → 게시글 작성자 알림 저장 | 📋 |
| 44 | 블로그 글 작성 → 구독자 알림 저장 | 📋 |
| 45 | 채팅 메시지 → 오프라인 상대방 FCM 알림 | 📋 |
| 46 | 로그아웃 → FCM 토큰 비활성화 → 알림 미발송 | 📋 |
| 47 | 신규 가입 → 환영 포인트 지급 이벤트 | 📋 |
| 48 | 블로거 구독 → 새 글 알림 수신 → 피드 갱신 | 📋 |
| 49 | 채팅방 생성 → 참여자 2명 검증 | 📋 |
| 50 | 게시글 삭제 → 관련 댓글 소프트 삭제 | 📋 |
| 51 | 사용자 탈퇴 → FCM 토큰 전체 비활성화 | 📋 |
| 52 | 좋아요 추가/취소 → likes_count 동시성 안전성 | 📋 |
| 53 | 게시글 검색 — 한글 키워드 검색 | 📋 |
| 54 | 블로그 피드 페이지네이션 정확성 | 📋 |
| 55 | 알림 읽음 처리 → unread_count 즉시 반영 | 📋 |
| 56 | 채팅 메시지 이력 역순 정렬 검증 | 📋 |

---

## Phase 6: Performance Tests 📋 (0/8)

**도구**: Locust
**예정**: 2026-03-14

| # | 테스트 시나리오 | 목표 | 상태 |
|---|--------------|------|------|
| 57 | 게시글 목록 조회 — 100 동시 사용자 | p95 < 200ms | 📋 |
| 58 | 게시글 작성 — 50 동시 사용자 | p95 < 500ms | 📋 |
| 59 | WebSocket 채팅 — 100 동시 연결 | 메시지 지연 < 50ms | 📋 |
| 60 | 블로그 피드 — 구독자 1,000명 | p95 < 300ms | 📋 |
| 61 | FCM 알림 발송 — 1,000명 동시 | 발송 완료 < 5초 | 📋 |
| 62 | DB Connection Pool 부하 테스트 | 풀 고갈 없음 | 📋 |
| 63 | Rate Limit 동작 검증 | 초과 시 429 | 📋 |
| 64 | Redis 캐시 히트율 측정 | 히트율 > 70% | 📋 |

---

## Phase 7: Flutter E2E Tests 📋 (0/10)

**도구**: Flutter Integration Test
**예정**: 2026-03-15

| # | 테스트 시나리오 | 상태 |
|---|--------------|------|
| 65 | Google 로그인 → JWT 저장 → 자동 로그인 | 📋 |
| 66 | 채팅방 생성 → WebSocket 연결 → 메시지 전송/수신 | 📋 |
| 67 | 게시글 작성 → 목록에서 확인 | 📋 |
| 68 | 댓글 작성 → 알림 수신 | 📋 |
| 69 | 블로거 구독 → 피드에서 글 확인 | 📋 |
| 70 | 알림 탭 → 읽음 처리 → 뱃지 제거 | 📋 |
| 71 | 로그아웃 → 재로그인 | 📋 |
| 72 | 오프라인 → 온라인 전환 → 채팅 재연결 | 📋 |
| 73 | 북마크 추가 → 북마크 목록 확인 | 📋 |
| 74 | 블로그 좋아요 → 카운트 즉시 반영 | 📋 |

---

## 테스트 실행 명령어

```bash
# Phase별 실행
pytest tests/ -v -m "phase1" --asyncio-mode=auto
pytest tests/ -v -m "phase2" --asyncio-mode=auto
pytest tests/ -v -m "phase3" --asyncio-mode=auto

# 전체 실행
pytest tests/ -v --asyncio-mode=auto --cov=app --cov-report=term-missing

# 빠른 스모크 테스트 (Phase 1+2만)
pytest tests/ -v -m "phase1 or phase2" -x

# 성능 테스트 (Locust)
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

---

## 관련 문서

- [V/20_test_cases.md](20_test_cases.md) — 상세 테스트 케이스 코드
- [R/40_traceability.md](../R/40_traceability.md) — 유저 스토리 ↔ 테스트 연결

---

## Execution Result (2026-03-20 push endpoint alignment)

1. Command: `python -m py_compile app/api/v1/endpoints/push.py app/domain/push/services/push_service.py tests/conftest.py`
   - Result: PASS
2. Command: `.venv/bin/pytest -q tests/test_push_endpoints.py`
   - Result: PASS (21 passed)
3. Notes:
   - 토큰 삭제는 인증 사용자 소유 토큰만 처리하도록 보강
   - 알림 삭제 엔드포인트와 토큰 갱신 계약을 앱 구현 기준으로 정렬
