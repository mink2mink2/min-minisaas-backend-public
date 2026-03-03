# I/20 — 변경 이력 (Change Log)

> 모든 의미 있는 변경사항을 날짜순으로 기록한다.
> 형식: `[날짜] - [카테고리] - [내용]`
> 카테고리: `feat` (신기능), `fix` (버그수정), `refactor` (리팩토링), `docs` (문서), `test` (테스트), `security` (보안), `infra` (인프라)

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
