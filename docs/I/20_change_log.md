# I/20 — 변경 이력 (Change Log)

> 모든 의미 있는 변경사항을 날짜순으로 기록한다.
> 형식: `[날짜] - [카테고리] - [내용]`
> 카테고리: `feat` (신기능), `fix` (버그수정), `refactor` (리팩토링), `docs` (문서), `test` (테스트), `security` (보안), `infra` (인프라)

---

## 2026-03-04 (PDF Helper 버그픽스 세션)

### fix: PDF 업로드 스트림 소진 문제 수정
- `files.py`: `file.read()` 후 스트림 소진 → `BytesIO(content)`로 재래핑
- `from io import BytesIO` import를 함수 내부 → 파일 상단으로 이동 (모듈성 준수)

### fix: UUID 타입 비교 오류 수정 (403 Forbidden)
- `files.py`, `convert.py`: `pdf_file.user_id != current_user.user_id` → `str()` 변환 비교
- 원인: SQLAlchemy UUID 객체 vs AuthResult str 타입 불일치

### fix: SQLAlchemy ENUM 타입 불일치 수정
- `pdf_file.py`: `SAEnum(FileType)` → `SAEnum(FileType, native_enum=False, values_callable=...)`
- 원인: 마이그레이션은 String 컬럼, 모델은 PostgreSQL ENUM 타입 요구 불일치

### fix: EventBus coroutine never awaited 수정
- `events.py`: `asyncio.iscoroutinefunction()` 체크 방식 → `inspect.isawaitable(result)` 방식으로 변경
- 원인: bound method에서 `iscoroutinefunction()`이 False 반환하는 경우 발생

### fix: CSV 한글 깨짐 수정
- `pdf_converter_service.py`: `encoding="utf-8"` → `encoding="utf-8-sig"` (BOM 추가)

### 4가지 원칙 검사 결과 (2026-03-04)
- **모듈성** ✅ BytesIO import 수정 완료 / ⚠️ 기술부채: files.py 라우터에 비즈니스 로직 혼재
- **독립성** ✅ 도메인 간 직접 의존 없음
- **이벤트 드리븐** ⚠️ events.py 수정 완료 / 기술부채: 일부 이벤트 미연결
- **보안** 🔴 운영 전 필수: `FIREBASE_PROJECT_ID` 실제 값 주입 필요

## 2026-03-06

### feat: coin simulator 대시보드/제어 API 추가
- `api/v1/endpoints/coin_simulator.py` 추가
  - `GET /api/v1/coin-simulator/dashboard`
  - `POST /api/v1/coin-simulator/start`
  - `POST /api/v1/coin-simulator/stop`
  - `PUT /api/v1/coin-simulator/settings`
- `domain/coin_simulator/services.py` 추가
  - 로컬 코인 서버 API 호출
  - Redis 캐시를 통한 대시보드 조회 최적화
  - start/stop/설정 저장 후 캐시 즉시 갱신
- `domain/coin_simulator/schemas.py` 추가
  - 상태/자산/포지션/거래/설정/권한 스키마 정의

### fix: coin simulator 조회 fallback 보강
- live 서버 설정이 없거나 연결 실패 시 `GET /api/v1/coin-simulator/dashboard`는 503 대신 mock 대시보드 반환
- 응답에 `data_source`, `notice`를 포함해 앱이 mock/live/cache 상태를 명시적으로 표시할 수 있게 조정
- start/stop/settings 제어 API는 기존처럼 live 서버 연결이 필요하며, 실패 시 503 유지

### security: coin simulator 제어 보호 강화
- `POST /api/v1/coin-simulator/start`, `POST /stop`, `PUT /settings`에 사용자별 rate limit 추가 (현재 5 req/min)
- control endpoint 성공/실패를 운영 로그에 감사 로그 형태로 기록
- 보안 리뷰 문서에 proxy/cache 운영 체크리스트 및 코드 검수 결과 반영

### feat: 설정 기반 superuser 응답 확장
- `core/config.py`: `SUPERUSER_EMAILS` 설정 추가
- `domain/auth/schemas/user.py`: `is_superuser` 필드 추가
- `/auth/me` 및 로그인 응답에 `is_superuser` 포함

### test: coin simulator 엔드포인트 테스트 추가
- `tests/test_coin_simulator_endpoints.py`
  - 일반 사용자 대시보드 조회
  - 일반 사용자 start 차단(403)
  - superuser 설정 저장 성공
  - live 미연결 시 mock fallback 반환

## 2026-03-18

### security: ledger 관리자 생성 API 보호 강화
- `POST /api/v1/verify/generate-daily/{date_str}`에 `verify_any_platform` 기반 사용자 인증 추가
- `SUPERUSER_EMAILS` 기준 관리자 권한 검증 추가
- 기존 `X-API-Key` 의존은 유지하되, API key 단독 호출을 차단

### security: ledger 조회 경로를 로그인 사용자 전용으로 전환
- `GET /api/v1/verify/integrity/{date_str}`, `GET /api/v1/verify/root/{date_str}`, `GET /api/v1/verify/today`에 `verify_any_platform + verify_api_key` 적용
- 원장 검증 기능을 공개 조회가 아니라 “로그인한 사용자가 자신의 원장과 시스템 원장을 대조하는 흐름”으로 재정의

### fix: board 공개 조회 optional auth 회귀 수정
- `board/posts.py`에 `_get_optional_user` 의존성 추가
- `GET /api/v1/board/posts`, `GET /api/v1/board/posts/{post_id}`에서 로그인 사용자의 반응 플래그 계산이 다시 동작하도록 수정
- `request` 미정의 예외를 광범위 `except`로 숨기던 경로 제거

### fix: blog 공개 조회 optional auth 회귀 수정
- `blog.py`의 `_get_optional_user`가 `authorization`, `db`를 포함해 `verify_any_platform`을 호출하도록 수정
- `GET /api/v1/blog/feed`, `GET /api/v1/blog/users/{user_id}`, `GET /api/v1/blog/posts/{post_id}`, `GET /api/v1/blog/search`에서 로그인 사용자 컨텍스트가 정상 반영되도록 보정

### test: ledger/board 보안 회귀 테스트 추가
- `tests/test_ledger_security.py` 추가
  - 일반 사용자 원장 생성 차단
  - superuser 원장 생성 허용
  - ledger 조회 경로 비인증 접근 차단
  - ledger 조회 경로 인증 사용자 접근 허용
- `tests/test_board_system.py`에 optional auth 사용자 컨텍스트 전달 검증 추가

### docs: RDIV 보안 수정 기록 추가
- `docs/rdiv/2026-03-18-authz-hardening-progress.md` 생성

### security: legacy auth 제거 및 앱 API 보호 정책 강화
- `app/api/v1/endpoints/auth/legacy.py` 제거
- `app/api/v1/endpoints/auth/__init__.py`에서 legacy router 제외
- 앱 미사용 구형 클라이언트 `SaaS/min-minisaas-app/lib/services/api_service.dart` 제거
- PDF 엔드포인트 전부를 `X-API-Key + 인증` 정책으로 강화
- `GET /api/v1/users/{user_id}`를 공개 stub에서 인증 필요 엔드포인트로 전환

### security: board/blog 읽기 경로를 로그인 사용자 전용으로 전환
- `GET /api/v1/board/posts`, `GET /api/v1/board/posts/{post_id}`, `GET /api/v1/board/posts/{post_id}/comments`, `GET /api/v1/board/categories`에 `verify_any_platform` 적용
- `GET /api/v1/blog/categories`, `GET /api/v1/blog/feed`, `GET /api/v1/blog/users/{user_id}`, `GET /api/v1/blog/posts/{post_id}`, `GET /api/v1/blog/search`에 `verify_any_platform` 적용
- 정책을 “앱 로그인 사용자만 조회 가능, 타인 콘텐츠 열람은 허용”으로 재정의

### test: 앱 API 읽기 경로 인증 필수 회귀 테스트 보강
- `tests/test_content_access_security.py` 추가
  - board/blog 읽기 경로가 인증 없이 호출되면 401/422를 반환하는지 검증
  - 인증된 사용자는 타인 콘텐츠를 정상 조회할 수 있는 정책을 유지하는지 검증

### security: logout CSRF를 선택 검증에서 필수 검증으로 전환
- `POST /api/v1/auth/logout`이 `X-CSRF-Token` 없이 진행되지 않도록 변경
- logout과 account deletion이 동일한 CSRF 검증 경로를 사용하도록 정리

### test: logout CSRF 필수 정책 회귀 검증
- `tests/test_csrf_protection.py`, `tests/test_auth_endpoints.py` 재검증
  - CSRF 누락 시 403
  - 유효 토큰만 logout 허용

### security: 공통 rate-limit 모듈 도입 및 주요 남용 경로 보호 강화
- `app/core/rate_limit.py` 추가
  - 고정 윈도우 기반 카운팅
  - `Retry-After` 헤더 포함 429 응답 공통화
  - IP 기준 / 사용자 기준 제한 공통 헬퍼 제공
- 로그인 엔드포인트 `POST /api/v1/auth/login/mobile`, `/login/kakao`, `/login/naver`에 분당 10회/IP 제한 추가
- `coin-simulator` 제어 rate limit을 공통 모듈로 이관
- 블로그 작성/수정/삭제/좋아요/구독, 채팅방 생성/메시지 전송, 푸시 토큰/알림 변경, 포인트 charge/consume/refund에 사용자 기준 rate limit 추가
- board 글/댓글 작성 429 응답에도 `Retry-After` 헤더를 포함하도록 보정
- board/blog/ledger 읽기 경로에도 사용자 기준 완만한 조회 rate limit(현재 분당 120회) 추가

### test: rate-limit 회귀 테스트 추가
- `tests/test_rate_limit.py` 추가
  - 공통 helper가 429 + `Retry-After`를 반환하는지 검증
  - 모바일 로그인 rate limit이 실제 엔드포인트에 적용되는지 검증
  - board 목록, ledger root 조회 rate limit이 실제 엔드포인트에 적용되는지 검증
- `tests/test_coin_simulator_endpoints.py`에 `Retry-After` 헤더 검증 추가

## 2026-03-28

### fix: Alembic metadata registry 누락 보정
- `app/db/model_registry.py`에 blog/push 도메인 모델 import를 추가
- `alembic check`/`autogenerate`가 `blog_*`, `push_*` 테이블을 삭제 후보로 오인하던 문제를 방지

### fix: `fcm_tokens.is_deleted` 스키마 drift 보정 migration 추가
- `alembic/versions/20260328_0012_fcm_tokens_basemodel_columns.py` 추가
- 개발 DB에 `alembic upgrade head` 적용 완료
- `fcm_tokens.is_deleted`를 backfill 후 `NOT NULL`로 정렬

### docs: RDIV 기준 문서에 Alembic drift 대응 원칙 기록
- `docs/R/20_acceptance_criteria.md`에 DB 스키마 안전성 인수 기준 추가
- `docs/D/20_data_model.md`에 push 관련 BaseModel 컬럼 보정 메모 추가
- `docs/D/90_decisions.md`에 registry 보정 + 수동 migration 우선 정책(ADR-010) 기록
- `docs/V/20_test_cases.md`에 migration 검증 케이스 추가

---

## 2026-03-04

### 🔄 발견: user.profile_updated API 실제 구현 상태 재분류
- **발견**: `PUT /users/me` 엔드포인트가 이미 구현되어 있음 (users.py:65-105)
  - nickname, name, picture 업데이트 기능 완전 작동
- **재분류**: Task 7 미구현 목록에서 "이벤트 발행 미구현"으로 상세화
  - API 자체는 ✅ 구현됨
  - ⚠️ EventBus 퍼블리시만 `user.profile_updated` 미구현
- **영향**: Task 7 구현률 재계산 필요 (25→26 이벤트 포함 재검토)

### docs: 이벤트 드리븐 아키텍처 검증 및 문서화
- **전체 코드베이스 검토** — 모든 domain services & endpoints 분석
- **이벤트 발행 현황 매핑** — 25/53 이벤트만 구현됨 (47% 구현율)
- **미구현 이벤트 목록 작성**:
  - P0: user.profile_updated (users.py:65-99 미발행)
  - P1: blog.post.updated/deleted (blog_service.py 미발행)
  - P2: blog.author.subscribed/unsubscribed (미발행)
  - P2: board.post.bookmarked (불일치: likes는 발행)
- **RDIV 문서 갱신**:
  - `I/10_implementation_plan.md` — Task 7 추가 (이벤트 검증)
  - `I/20_change_log.md` — 변경 기록 (이 항목)
  - `/min-minisaas/doc/EVENT_DRIVEN.md` — 이벤트 카탈로그 업데이트 (메인 레포)

### 이벤트 구현 현황

**완전 구현 (100%)**
- ✅ Board Posts & Comments (모든 CRUD + reactions)
- ✅ Chat (room creation, message sending)
- ✅ Points (charge, consume, refund)
- ✅ PDF (file operations)

**부분 구현 (<50%)**
- 🟡 Chat: room/message 일부만
- 🟡 Blog: create only
- 🟡 User: auth events만

**미구현 (0%)**
- ❌ Blog updates/deletes/subscriptions
- ❌ User profile updates
- ❌ Board bookmarks (inconsistent)
- ❌ Notifications

---

## 2026-03-03

### docs: RDIV 문서 구조 생성
- `docs/` 전체 RDIV 구조 최초 생성
- README.md — 아키텍처 규칙 및 DoD 정의
- R/ — 요구사항 문서 4개
- D/ — 설계 문서 4개 (아키텍처, 데이터모델, API 계약, ADR)
- I/ — 구현 계획, 변경이력, 배포 가이드
- V/ — 테스트 계획, 테스트 케이스, 보안 체크리스트, 관찰성
- AI/ — AI 컨텍스트 팩, 코딩 규칙, 작업 큐, Runbook

---

## 2026-03-01

### feat: Push 백엔드 전체 구현 완료
- `domain/push/models.py` — FCMToken, PushNotification ORM 모델 추가
- `domain/push/schemas.py` — 요청/응답 Pydantic 스키마 추가
- `domain/push/services.py` — FCM 토큰 CRUD, 알림 조회/읽음/삭제 서비스 구현
- `domain/push/fcm_service.py` — Firebase Admin SDK FCM 발송 로직 분리
- `domain/push/handlers.py` — EventBus 핸들러 4개 등록
  - `board.post.created` → 댓글 알림
  - `board.comment.created` → 게시글 작성자 알림
  - `blog.post.created` → 구독자 알림
  - `chat.message.received` → 오프라인 사용자 알림
- `api/v1/endpoints/push.py` — Push API 8개 엔드포인트 구현
- `GET /api/v1/push/notifications/unread/count` 엔드포인트 추가
- Alembic 마이그레이션 — `fcm_tokens`, `push_notifications` 테이블 추가

**코드 규모**: ~1,195 lines 추가

---

## 2026-02-25

### feat: Push 도메인 기반 구조 추가
- `core/fcm.py` — Firebase Admin SDK 초기화 모듈 추가
- `core/events.py` — EventBus 클래스 구현 (subscribe/publish)
- `domain/push/` 디렉토리 생성

### security: FCM 서비스 계정 키 환경변수화
- `FIREBASE_CREDENTIALS_PATH` 환경변수로 키 파일 경로 관리
- 서비스 계정 JSON을 코드에 직접 포함하는 방식 제거

---

## 2026-02-22

### feat: Blog 백엔드 전체 구현 완료
- `domain/blog/models.py` — BlogPost, BlogLike, BlogSubscription ORM 모델 추가
- `domain/blog/schemas.py` — 요청/응답 스키마 추가
- `domain/blog/services.py` — CRUD, 구독, 피드, 좋아요 서비스 구현
- `domain/blog/handlers.py` — 블로그 글 발행 이벤트 핸들러
- `api/v1/endpoints/blog.py` — Blog API 엔드포인트 구현
- Alembic 마이그레이션 — `blog_posts`, `blog_likes`, `blog_subscriptions` 테이블 추가

**코드 규모**: ~1,000 lines 추가

---

## 2026-02-20

### feat: Blog 도메인 구독 API 추가
- `POST /api/v1/blogs/{id}/subscribe` — 블로거 구독
- `DELETE /api/v1/blogs/{id}/subscribe` — 구독 취소
- Flutter 앱 블로그 구독 버튼 연동 완료

### fix: Blog slug 중복 처리 개선
- 동일 제목 게시글 작성 시 slug 뒤에 숫자 자동 추가 (`-2`, `-3`, ...)
- 기존 `UNIQUE constraint` 오류 발생하던 문제 수정

---

## 2026-02-19

### feat: Blog 백엔드 구현 시작
- `domain/blog/` 디렉토리 생성
- BlogPost 모델 및 기본 CRUD 구현

---

## 2026-02-18

### feat: Board 백엔드 전체 구현 완료
- `domain/board/models.py` — BoardPost, BoardComment, BoardReaction ORM 모델 추가
- `domain/board/services.py` — CRUD, 좋아요, 북마크, 검색 서비스 구현
- `domain/board/handlers.py` — 게시글 생성/댓글 이벤트 발행
- `api/v1/endpoints/board.py` — Board API 엔드포인트 구현
- Alembic 마이그레이션 — `board_posts`, `board_comments`, `board_reactions` 테이블 추가

**코드 규모**: ~800 lines 추가

---

## 2026-02-15

### feat: Push API 연동 완료 (Flutter)
- Flutter 앱에서 FCM 토큰 자동 등록 구현
- 알림 탭 화면 구현

### feat: Board 검색 기능 추가
- `GET /api/v1/board/posts?search={keyword}` 파라미터 지원
- PostgreSQL `ilike` 기반 제목/내용 검색 구현

### security: Rate Limiting 적용
- `middleware/rate_limit.py` — SlowAPI 기반 Rate Limit 미들웨어 추가
- 게시글 작성: 10개/분
- 댓글 작성: 1개/초
- 로그인: 10 req/min per IP

---

## 2026-03-18

### fix: authz hardening 후속 런타임 이슈 정리
- `app/core/rate_limit.py` — Redis 연결 실패 시 fail-open으로 처리해 로그인/일반 요청이 500으로 무너지지 않도록 수정
- `app/core/events.py` — async 이벤트 핸들러 스케줄링 누락 수정 (`asyncio` import)
- `app/domain/push/events/push_event_handlers.py` — board post/comment 알림에서 `post.user_id` 대신 `post.author_id` 사용
- `alembic/versions/20260318_0011_push_notifications_basemodel_columns.py` — `push_notifications.updated_at`, `is_deleted` 보정 마이그레이션 추가 및 적용

### fix: UI 표시 이름 계약 보강
- `app/domain/chat/schemas/chat.py` + `app/api/v1/endpoints/chat.py` — chat message 응답에 `sender_name` 추가
- `app/domain/board/schemas/comment.py` + `app/api/v1/endpoints/board/comments.py` — board comment 작성자 `nickname` 응답 추가
- Flutter 앱에서 chat/blog 작성자 표기를 `nickname ?? name` 우선으로 수정

### release: app version bump
- `SaaS/min-minisaas-app/pubspec.yaml` 버전을 `1.0.15+15`로 상향

---

## 2026-02-14

### feat: Board 백엔드 구현 시작
- `domain/board/` 디렉토리 생성
- BoardPost 모델 및 기본 CRUD 구현

---

## 2026-02-13

### feat: Chat Flutter 앱 구현 완료
- 소셜 로그인 화면 (Google, Kakao, Naver)
- 채팅방 목록 화면
- 실시간 채팅 화면 (WebSocket)
- JWT 보안 저장소 (`flutter_secure_storage`) 연동

**코드 규모**: ~600 lines 추가

## 2026-03-20

### fix: Push endpoint ownership and app contract alignment
- `app/domain/push/services/push_service.py`에서 토큰 갱신을 `token_id` 기준으로 수정했다.
- `app/domain/push/services/push_service.py`에서 토큰 삭제/알림 읽음/알림 삭제 시 사용자 소유 검증을 추가했다.
- `app/api/v1/endpoints/push.py`에 `DELETE /api/v1/push/notifications/{id}` 엔드포인트를 추가했다.
- `tests/conftest.py`, `tests/test_push_endpoints.py` 기준으로 푸시 엔드포인트 계약을 재검증했다.

---

## 2026-02-11

### feat: Chat 백엔드 전체 구현 완료
- `domain/auth/` — 소셜 로그인 서비스, JWT 발급 구현
- `core/auth/google.py` — Firebase ID Token 검증
- `core/auth/kakao.py` — 카카오 API 서버사이드 검증
- `core/auth/naver.py` — 네이버 API 서버사이드 검증
- `domain/chat/` — 채팅방/메시지 도메인 구현
- `api/v1/endpoints/auth.py` — 인증 API (5개 엔드포인트)
- `api/v1/endpoints/chat.py` — Chat API + WebSocket
- `middleware/auth.py` — JWT 인증 미들웨어
- `main.py` — 앱 초기화
- Alembic 마이그레이션 초기 설정

**코드 규모**: ~500 lines 추가

---

## 2026-02-05

### infra: 프로젝트 초기 설정
- FastAPI 프로젝트 구조 생성
- `core/config.py` — Pydantic BaseSettings 환경변수 설정
- `core/database.py` — SQLAlchemy AsyncEngine + get_db()
- `core/cache.py` — Redis 클라이언트 + get_cache()
- Alembic 초기화
- `requirements.txt` / `pyproject.toml` 설정
- `.env.example` 파일 생성

---

## 2026-02-01

### docs: 프로젝트 설계 완료
- 도메인 정의 및 아키텍처 설계
- DB 스키마 초안 작성
- API 엔드포인트 목록 작성
- 기술 스택 결정 (ADR 작성)
# 2026-03-28

- fix: FCM 발송 경로를 Firebase Admin SDK의 모듈 함수 기반으로 수정.
  - `app/domain/push/services/fcm_service.py`: `messaging.client()`/`client.send_multicast()` 의존을 제거하고 `initialize_firebase()` 후 `messaging.send()` 및 topic 함수 직접 호출로 변경.
  - FCM 토큰 로그는 masked 형태로 남기도록 조정.
  - `tests/test_fcm_service.py`: SDK 호출 패턴 변경에 맞춰 mocking 전략 업데이트.
