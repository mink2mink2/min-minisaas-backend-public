# min-minisaas Backend — 문서 목록

**최종 업데이트**: 2026-02-16

## 🚀 빠른 시작 (5분)

👉 **먼저 읽기**: 
1. `IMPLEMENTATION_STATUS.md` — 전체 모듈 현황
2. `DB_SCHEMA_OVERVIEW.md` — DB 테이블 구조
3. `DB_MIGRATION_WORKFLOW.md` — DB 마이그레이션 절차

---

## 📖 세부 문서

### 현황 (최신)
- **`IMPLEMENTATION_STATUS.md`** ⭐
  - 모든 모듈 API/Models/Services 정리
  - 완성도, 테스트 상태
  - 다음 Task

### 데이터베이스
- **`DB_SCHEMA_OVERVIEW.md`**
  - 전체 테이블 구조
  - 관계도
  - 각 컬럼 설명

- **`DB_MIGRATION_WORKFLOW.md`**
  - Alembic 마이그레이션 절차
  - 생성/검증/롤백 방법
  - DevOps 가이드

### 아키텍처 (참고용)
- **`backup/CHAT_BACKEND_IMPLEMENTATION_2026_02_16.md`**
  - Chat MVP 구현 상세 기록
  - searchUsers API
  - get_or_create_one_to_one_room 로직
  - Event handlers

- **`backup/CHAT_BACKEND_QUICKSTART.md`**
  - Chat 핵심 API 요약

---

## 📂 코드 위치

```
app/domain/
├── auth/
│   ├── models/ (User, Device, SecurityLog)
│   ├── schemas/ (user, csrf)
│   └── services/
│       └── auth_service.py

├── board/ (완성)
│   ├── models/ (Post, Comment, Category, Like, Bookmark)
│   ├── schemas/ (post, comment, category)
│   ├── services/ (post_service.py, comment_service.py)
│   └── API: 25개+ endpoints

├── blog/ (완성)
│   ├── models/ (BlogPost, BlogCategory, Like, Subscription, Comment)
│   ├── schemas/ (post, category)
│   ├── services/ (blog_service.py)
│   ├── events/ (event handlers)
│   └── API: 20개+ endpoints

├── chat/ (완성)
│   ├── models/ (ChatRoom, ChatRoomMember, ChatMessage)
│   ├── schemas/ (chat.py)
│   ├── services/
│   │   ├── chat_service.py
│   │   ├── realtime_gateway.py
│   │   └── chat_event_handlers.py
│   └── API: 5개 + WS

├── push/ (구현)
│   ├── models/ (Notification)
│   ├── schemas/ (push.py)
│   ├── services/
│   │   └── push_service.py
│   └── API: 15개+

├── pdf/ (부분)
│   ├── models/ (PdfFile)
│   ├── schemas/ (pdf_file.py)
│   └── services/ (pdf_converter_service.py, pdf_file_service.py)

└── points/ (부분)
    ├── schemas/ (points.py)
    └── services/ (point_service.py, ledger_service.py)

app/api/v1/endpoints/
├── auth/ (7개, 모든 플랫폼)
├── board/ (25개+)
├── blog.py (20개+)
├── chat.py (5개 + WS)
├── push.py (15개+)
├── pdf/ (10개+)
├── users.py (검색 포함)
└── ...
```

---

## 🔧 로컬 개발 셋업

### 1️⃣ 초기 설정
```bash
# 환경 변수
cp .env.example .env
# .env 에서 비밀번호/토큰 설정

# DB 자동 설정
make setup
# → bootstrap + migrate + verify 자동 실행

# 또는 수동
make bootstrap    # DB 생성
make migrate      # alembic upgrade head
make verify       # postgres/redis 연결 확인
```

### 2️⃣ 실행
```bash
# Docker
docker-compose up -d

# 또는 로컬
pip install -r api/requirements.txt
python api/app/main.py
```

### 3️⃣ API 확인
```
http://localhost:8000/docs (Swagger UI)
```

---

## 🧪 테스트

```bash
# 모든 테스트
pytest tests/ -v

# 특정 모듈
pytest tests/test_chat_endpoints.py -v
pytest tests/test_auth_endpoints.py -v
pytest tests/test_board_endpoints.py -v

# 현재 상태
# 76/76 tests PASSING ✅
```

---

## 📋 API 요약

### Auth (7개 endpoints)
- `POST /auth/login/mobile` — Firebase JWT
- `POST /auth/login/web` — Session + Cookie
- `POST /auth/login/desktop` — PKCE + Refresh
- `POST /auth/refresh/desktop` — Token 갱신
- `GET /auth/me` — 사용자 정보 + CSRF token
- `POST /logout` — 로그아웃 (CSRF 검증)
- `DELETE /account` — 계정 삭제 (CSRF 검증)

### Board (25개+)
- Posts: CRUD, 검색, 필터, 통계
- Comments: 목록, 작성, 삭제
- Categories: 목록
- Reactions: 좋아요, 북마크

### Blog (20개+)
- Feed: `GET /blog/feed`
- User Blog: `GET /blog/users/{user_id}`
- Posts: CRUD, 검색, 발행/draft
- Like: `POST /blog/posts/{id}/like`
- Subscribe: `POST /blog/posts/{id}/subscribe`
- Categories: `GET /blog/categories`

### Chat (5 + WS)
- Room List: `GET /chat/rooms` (상대 정보 포함)
- Create Room: `POST /chat/rooms`
- Messages: `GET/POST /chat/rooms/{room_id}/messages`
- WebSocket: `WS /chat/ws/rooms/{room_id}`
- User Search: `GET /users/search?q=...`

### Push (15개+)
- List, Get, Read, Delete
- Batch operations

### Others
- PDF Convert, Files
- Points Ledger
- ...

---

## 🛡️ 보안

### 완료된 Task (P1~P5)
- ✅ Token Reuse Detection
- ✅ Session Fixation Prevention
- ✅ Device Secret Rotation + Rate Limiting
- ✅ Unified Error Response
- ✅ CSRF Token Protection

### 인증 헤더 (필수)
```
X-API-Key: {API_SECRET_KEY}
X-Platform: mobile|web|desktop|device
Authorization: Bearer {token}  (web은 session cookie)
X-CSRF-Token: {token}         (POST/DELETE에만 필수)
```

---

## 🎯 다음 Task

### Immediate (이번 주)
- [ ] Chat MVP: 사용자 검색 API 실제 테스트
- [ ] Chat MVP: 1:1 room 중복 방지 검증
- [ ] Blog: 댓글 API 추가 (선택)

### Short-term
- [ ] PDF: API Endpoint 추가
- [ ] Points: API Endpoint 추가
- [ ] App-Backend E2E 테스트

### Long-term
- [ ] mTLS for IoT (Infrastructure)
- [ ] HSM Secret Storage (Enterprise)
- [ ] Caching (Redis) 최적화

---

## 📁 주요 파일

```
.env.example          — 환경 변수 템플릿
docker-compose.yml    — 로컬 개발 스택
alembic/
  versions/           — 마이그레이션 파일들
    20260215_0004_*   — Chat domain
  env.py
  script.py.mako
requirements.txt      — Python 의존성
api/
  app/
    main.py           — FastAPI 진입점
    core/
      database.py     — DB 연결
      events.py       — Event bus
    api/v1/
      endpoints/      — 모든 라우터
      dependencies/   — 인증, 검증
```

---

## 🔍 문제 발생 시

| 문제 | 원인 | 해결 |
|------|------|------|
| DB 마이그레이션 실패 | 스키마 충돌 | `make verify` 후 상태 확인 |
| Redis 연결 실패 | REDIS_URL 미설정 | `.env` 에서 `REDIS_URL` 확인 |
| API 401 | API_SECRET_KEY 불일치 | App dart-define과 Backend .env 일치 확인 |
| WS 연결 안 됨 | 인증 헤더 빠짐 | Authorization + X-API-Key 확인 |
| Chat 메시지 안 옴 | Event bus 미작동 | EventBus 초기화 확인 |

---

## 📚 추가 참고

- Backend 초기 설계: `../min-minisaas/docs/` (별도 프로젝트)
- App-Backend 호환성: App의 `docs/IMPLEMENTATION_STATUS.md` 비교
- 실제 구현 로그: `docs/backup/` 폴더

---

**Last Updated**: 2026-02-16  
**유지자**: Claude Haiku
