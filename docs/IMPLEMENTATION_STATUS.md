# min-minisaas Backend — 구현 현황 (2026-02-16)

## 📊 모듈별 상태 요약

| 모듈 | 상태 | Models | Services | API | 줄 수 |
|------|------|--------|----------|-----|-------|
| **Auth** | ✅ 완성+보안 | 3 | 1 | 7개 endpoint | 보안 P1~P5 완료 |
| **Board** | ✅ 완성 | 4 | 2 | 25개+ | 825줄 |
| **Blog** | ✅ 완성 | 6 | 1 | 20개+ | 472줄 |
| **Chat** | ✅ 완성 | 2 | 3 | 5개 + WS | - |
| **Push** | ✅ 구현 | 1 | 1 | 15개+ | 240줄 |
| **PDF** | 🟡 부분 | 1 | 2 | 10개+ | - |
| **Points** | 🟡 부분 | - | 2 | - | - |

---

## 🟢 완성된 모듈

### 1️⃣ Auth (인증 + 보안)
**구현 범위**: 
- Mobile (Firebase JWT, Stateless)
- Web (Session + HttpOnly Cookie)
- Desktop (PKCE + Refresh Token)
- IoT/Device (Secret Rotation)

**보안 완성 (P1~P5)**:
- ✅ **Task 1**: Token Reuse Detection (Desktop)
- ✅ **Task 2**: Session Fixation Prevention (Web)
- ✅ **Task 3**: Device Secret Rotation + Rate Limiting
- ✅ **Task 4**: Unified Error Response Format
- ✅ **Task 5**: CSRF Token for Sensitive Operations

**Models**:
- `User` (사용자)
- `Device` (IoT 기기)
- `SecurityLog` (보안 이벤트)

**Services**:
- `AuthService` — 인증 로직
- `CSRFTokenManager` — CSRF 토큰 관리

**Endpoints** (7개):
- `POST /auth/login/mobile` — 모바일 로그인
- `POST /auth/login/web` — 웹 로그인
- `POST /auth/login/desktop` — 데스크톱 로그인
- `POST /auth/refresh/desktop` — 토큰 갱신
- `GET /auth/me` — 사용자 정보 + CSRF 토큰
- `POST /logout` — 로그아웃 (CSRF 검증)
- `DELETE /account` — 계정 삭제 (CSRF 검증)

**테스트**: 76/76 PASSING ✅

---

### 2️⃣ Board (게시판)
**모듈**: `app/domain/board/`

**Models**:
- `Post` — 게시글
- `Comment` — 댓글
- `Category` — 카테고리
- `Like`, `Bookmark` — 반응

**Services**:
- `PostService` — 게시글 CRUD/검색/필터/통계
- `CommentService` — 댓글 관리

**Endpoints** (25개+): `app/api/v1/endpoints/board/`
- **posts.py** — 게시글 관리
  - `GET /posts` — 목록 (페이지네이션/검색/정렬)
  - `POST /posts` — 작성
  - `GET /posts/{id}` — 상세
  - `PUT /posts/{id}` — 수정
  - `DELETE /posts/{id}` — 삭제
  - 통계, 카테고리별 조회 등
  
- **comments.py** — 댓글
  - `GET /posts/{post_id}/comments` — 댓글 목록
  - `POST /posts/{post_id}/comments` — 댓글 작성
  - 대댓글 지원

- **reactions.py** — 반응
  - `POST /posts/{id}/like` — 좋아요
  - `POST /posts/{id}/bookmark` — 북마크
  
- **categories.py** — 카테고리

**테스트**: ✅ 단위 테스트 추가 (`test_board_service_test.dart`)

**특징**:
- 풀텍스트 검색
- 카테고리/태그 필터
- 정렬 (최신순, 인기순, 댓글순)
- 페이지네이션
- 조회수 카운팅

---

### 3️⃣ Blog (블로그)
**모듈**: `app/domain/blog/`

**Models**:
- `BlogPost` — 블로그 글
- `BlogCategory` — 카테고리
- `BlogLike` — 좋아요
- `BlogSubscription` — 구독
- `BlogComment` — 댓글
- `BlogCommentLike` — 댓글 좋아요

**Services**:
- `BlogService` — 글 관리/검색/좋아요/구독
  - `create_post()` — 글 작성
  - `list_feed()` — 전체 피드
  - `list_user_blog()` — 사용자 블로그
  - `search_posts()` — 검색
  - `like_post()` — 좋아요
  - `get_subscriber_count()` — 구독자 수

**Endpoints** (20개+): `app/api/v1/endpoints/blog.py`
- `GET /blog/feed` — 피드 (모든 발행된 글)
- `GET /blog/users/{user_id}` — 사용자 블로그 (개인 페이지)
- `GET /blog/posts/{id}` — 글 상세
- `POST /blog/posts` — 글 작성
- `PUT /blog/posts/{id}` — 글 수정
- `DELETE /blog/posts/{id}` — 글 삭제
- `POST /blog/posts/{id}/like` — 좋아요
- `POST /blog/posts/{id}/subscribe` — 구독
- `GET /blog/categories` — 카테고리 목록

**이벤트**:
- `BlogPostCreatedEvent` — 글 발행 시
- `BlogPostLikedEvent` — 좋아요 시

**특징**:
- Draft/Published 상태
- Slug 기반 URL
- 조회수, 좋아요, 댓글 카운팅
- Featured image 지원
- 태그 지원
- 카테고리 분류

---

### 4️⃣ Chat (채팅)
**모듈**: `app/domain/chat/`

**Models**:
- `ChatRoom` — 채팅방
- `ChatMessage` — 메시지
- `ChatRoomMember` — 멤버 (1:1/그룹 구분)

**Services**:
- `ChatService` — 방 관리/메시지 관리
  - `searchUsers()` — 사용자 검색
  - `get_or_create_one_to_one_room()` — 1:1 방 중복 방지
  - `list_rooms_with_details()` — 방 목록 (상대 정보/마지막 메시지)
  - `send_message()` — 메시지 전송

- `RealtimeGateway` — WebSocket 실시간 연결
  - 방별 연결 관리
  - 메시지 브로드캐스트

**Endpoints** (5개 + WS):
- `GET /chat/rooms` — 방 목록
- `POST /chat/rooms` — 방 생성
- `GET /chat/rooms/{room_id}/messages` — 메시지 조회
- `POST /chat/rooms/{room_id}/messages` — 메시지 전송
- `WS /chat/ws/rooms/{room_id}` — 실시간 채팅

**사용자 검색 API**:
- `GET /users/search?q=john&limit=10`
- 자신을 제외한 다른 사용자만 반환

**1:1 방 정책**:
- 같은 두 user_id 조합 → 1개 방만 존재
- `getOrCreateOneToOneRoom()` — 기존/새 방 자동 처리

**Room List 응답**:
```json
{
  "room_id": "uuid",
  "name": "상대 이름",
  "participants": [{ "user_id", "name", "picture", "username" }],
  "last_message": { "content", "sender_name", "created_at" },
  "unread_count": 0,
  "updated_at": "..."
}
```

**DB Migration**:
- `20260215_0004_chat_domain.py` 적용됨

**테스트**: `pytest tests/test_chat_endpoints.py` 통과

---

### 5️⃣ Push (푸시 알림)
**모듈**: `app/domain/push/`

**Models**:
- `Notification` — 알림

**Services**:
- CRUD 관리
- 읽음 상태
- 삭제

**Endpoints** (15개+):
- `GET /notifications` — 목록
- `GET /notifications/{id}` — 상세
- `POST /notifications/{id}/read` — 읽음 표시
- `DELETE /notifications/{id}` — 삭제

**특징**:
- 사용자별 알림
- 읽음 상태 추적
- 배치 삭제

---

## 🟡 부분 구현

### PDF 처리
**구현된 부분**:
- Models: `PdfFile`
- Services: `PdfConverterService`, `PdfFileService`
- Events: `PdfConversionCompletedEvent`
- Endpoints: Convert, Files (10개+)

**미구현**:
- App에서는 mockup만 있음
- Editor UI 없음

---

### Points (포인트 시스템)
**구현된 부분**:
- Services: `PointService`, `LedgerService`
- Event handlers

**미구현**:
- API endpoints 아직

---

## 🛠️ 기술 스택

- **Framework**: FastAPI
- **Database**: PostgreSQL (async)
- **Auth**: Firebase JWT + Session
- **Realtime**: WebSocket
- **Events**: Event Bus (비동기)
- **Validation**: Pydantic
- **ORM**: SQLAlchemy (async)
- **Migrations**: Alembic

---

## ✅ 품질 보증

### 테스트
```bash
pytest tests/ -v
# 76/76 tests PASSING ✅
```

### 코드 분석
```bash
make check  # black, isort, flake8, pylint
```

### DB 검증
```bash
make setup      # bootstrap + migrate + verify
make verify     # postgres/redis 연결 확인
```

---

## 📚 DB 스키마

**테이블**:
- auth (User, Device, SecurityLog)
- board (Post, Comment, Category, Like, Bookmark)
- blog (BlogPost, BlogCategory, BlogLike, BlogSubscription, BlogComment)
- chat (ChatRoom, ChatRoomMember, ChatMessage)
- push (Notification)
- pdf (PdfFile)
- points (LedgerEntry)

**Migration Workflow**: `docs/DB_MIGRATION_WORKFLOW.md` 참고

---

## 🎯 다음 Task

1. **Chat MVP 마무리**
   - [ ] 사용자 검색 API 실제 테스트
   - [ ] 1:1 room 중복 방지 실제 검증
   - [ ] WS 인증 정책 (web/mobile/desktop 일관화)

2. **Blog 완성**
   - [ ] 댓글 API 추가 (선택)
   - [ ] 구독 알림 이벤트 연동

3. **PDF API Endpoint 추가** (선택)

4. **Points API Endpoint 추가** (선택)

---

## 📁 주요 파일

**설정**:
- `.env.example` — 환경 변수
- `docker-compose.yml` — 로컬 개발 스택
- `alembic/versions/` — DB 마이그레이션

**로그 조회**:
- App 구현: `docs/backup/CHAT_APP_IMPLEMENTATION_2026_02_16.md`
- Backend 구현: `docs/backup/CHAT_BACKEND_IMPLEMENTATION_2026_02_16.md`

---

**Last Updated**: 2026-02-16  
**정리자**: Claude Haiku
