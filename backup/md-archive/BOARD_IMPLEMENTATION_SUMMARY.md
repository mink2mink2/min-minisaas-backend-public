# Board System 구현 현황

**작성일**: 2026-02-15
**상태**: ✅ 완료 (마이그레이션 대기중)
**버전**: Phase 2.5 완료

---

## 📋 목차

1. [구현 완료 항목](#구현-완료-항목)
2. [파일 구조](#파일-구조)
3. [API 엔드포인트](#api-엔드포인트)
4. [주요 기능](#주요-기능)
5. [다음 단계](#다음-단계)

---

## 구현 완료 항목

### ✅ Phase 1: 모델 (6개)

| 모델 | 파일 | 설명 |
|------|------|------|
| `BoardCategory` | `models/category.py` | 게시판 카테고리 |
| `BoardPost` | `models/post.py` | 게시글 (PostStatus enum) |
| `Comment` | `models/comment.py` | 댓글 (max 2-level) |
| `PostLike` | `models/like_bookmark.py` | 게시글 좋아요 |
| `PostBookmark` | `models/like_bookmark.py` | 게시글 북마크 |
| `CommentLike` | `models/like_bookmark.py` | 댓글 좋아요 |

**특징:**
- UUID 기본 키
- 타임스탬프 자동 관리
- Soft delete 지원 (`is_deleted` 플래그)
- 외래키 제약조건
- 복합 UNIQUE 제약조건

### ✅ Phase 2: 모델 레지스트리

**파일**: `app/db/model_registry.py`

```python
# 추가된 imports
from app.domain.board.models.category import BoardCategory
from app.domain.board.models.post import BoardPost
from app.domain.board.models.comment import Comment
from app.domain.board.models.like_bookmark import PostLike, PostBookmark, CommentLike
```

### ✅ Phase 3: 스키마 (Pydantic)

| 스키마 | 파일 | 용도 |
|--------|------|------|
| `CategoryCreate`, `CategoryUpdate`, `CategoryResponse` | `schemas/category.py` | 카테고리 |
| `PostCreate`, `PostUpdate`, `PostResponse`, `PostListItem` | `schemas/post.py` | 게시글 (요약/상세) |
| `CommentCreate`, `CommentUpdate`, `CommentResponse` | `schemas/comment.py` | 댓글 (자기참조) |
| `AuthorBrief` | 공유 | 작성자 정보 |

**특징:**
- `AuthorBrief`: id, name, picture, username
- `PostListItem`: 목록용 요약 (is_liked, is_bookmarked)
- `PostResponse`: 상세 조회용
- `CommentResponse`: 자기참조 + `model_rebuild()`

### ✅ Phase 4: 서비스 (비즈니스 로직)

#### PostService (12개 메서드)

```python
# app/domain/board/services/post_service.py

# 레이트 제한
check_post_rate_limit(user_id)  # 10/min (Redis INCR)

# 컨텐츠
sanitize_content(raw, is_comment)  # HTML 태그 제거

# CRUD
create_post(author_id, title, content, ...)
list_posts(page, limit, category_id, sort, user_id)
get_post(post_id, user_id)
update_post(post_id, author_id, ...)
delete_post(post_id, author_id)

# 검색
search_posts(query, page, limit)  # FTS + trigram fallback

# 반응
toggle_like(post_id, user_id)  # 원자적 UPDATE
toggle_bookmark(post_id, user_id)  # 원자적 UPDATE
is_post_liked_by_user(post_id, user_id)
is_post_bookmarked_by_user(post_id, user_id)
```

#### CommentService (8개 메서드)

```python
# app/domain/board/services/comment_service.py

# 레이트 제한
check_comment_rate_limit(user_id)  # 1/sec (Redis SETNX)

# 컨텐츠
sanitize_content(raw)  # 모든 HTML 제거

# CRUD
create_comment(post_id, author_id, content, parent_id)  # 깊이 검증
get_comments(post_id)  # 트리 구조 반환
update_comment(comment_id, author_id, content)
delete_comment(comment_id, author_id)  # "[삭제됨]" 마스킹

# 반응
toggle_comment_like(comment_id, user_id)  # 원자적
is_comment_liked_by_user(comment_id, user_id)
```

**특징:**
- 레이트 제한: Redis 기반 (INCR, SETNX)
- 새니타이제이션: 정규식 기반 HTML 제거 (bleach 없음)
- 이벤트 발행: event_bus.emit() 호출
- 원자적 업데이트: UPDATE ... SET count = count + 1

### ✅ Phase 5: API 엔드포인트 (18개)

#### 카테고리 (4개)

```python
# app/api/v1/endpoints/board/categories.py

GET    /board/categories          (공개)
POST   /board/categories          (인증)
PUT    /board/categories/{id}     (인증)
DELETE /board/categories/{id}     (인증)
```

#### 게시글 (6개)

```python
# app/api/v1/endpoints/board/posts.py

GET    /board/posts               (공개, 페이지네이션)
POST   /board/posts               (인증, 레이트 10/min)
GET    /board/posts/{id}          (공개, view_count++)
PUT    /board/posts/{id}          (인증, 작성자만)
DELETE /board/posts/{id}          (인증, 작성자만)
GET    /board/search?q=...        (공개, FTS)
```

#### 댓글 (5개)

```python
# app/api/v1/endpoints/board/comments.py

GET    /board/posts/{id}/comments              (공개, 트리)
POST   /board/posts/{id}/comments              (인증, 레이트 1/sec)
POST   /board/posts/{id}/comments/{cid}/replies (인증)
PUT    /board/comments/{id}                    (인증, 작성자만)
DELETE /board/comments/{id}                    (인증, 작성자만)
```

#### 반응 (3개)

```python
# app/api/v1/endpoints/board/reactions.py

POST   /board/posts/{id}/like           (인증)
DELETE /board/posts/{id}/like           (인증)
POST   /board/posts/{id}/bookmark       (인증)
DELETE /board/posts/{id}/bookmark       (인증)
POST   /board/comments/{id}/like        (인증)
DELETE /board/comments/{id}/like        (인증)
```

**특징:**
- 모든 엔드포인트: `Depends(verify_api_key)` 필수
- 인증 엔드포인트: `Depends(verify_any_platform)` 사용
- 공개 엔드포인트: 선택적 인증 패턴 구현
- 에러 처리: HTTPException with 적절한 상태코드

### ✅ Phase 6: 통합

#### app/api/v1/__init__.py

```python
from app.api.v1.endpoints.board import board_router

api_router.include_router(board_router)
```

#### app/core/events.py (10개 이벤트 추가)

```python
BoardPostCreatedEvent(user_id, post_id, title, category_id)
BoardPostUpdatedEvent(user_id, post_id)
BoardPostDeletedEvent(user_id, post_id)
BoardPostViewedEvent(user_id, post_id)
BoardPostLikedEvent(user_id, post_id, liked)
BoardCommentCreatedEvent(user_id, post_id, comment_id)
BoardCommentUpdatedEvent(user_id, comment_id)
BoardCommentDeletedEvent(user_id, comment_id)
BoardCommentLikedEvent(user_id, comment_id, liked)
```

#### 삭제

- ❌ `app/api/v1/endpoints/posts.py` (스텁) 삭제

### ✅ Phase 7: 마이그레이션

**파일**: `alembic/versions/20260215_0002_board_system.py`

```python
# 생성되는 테이블
board_categories       # 카테고리
board_posts           # 게시글 + search_vector TSVECTOR
comments              # 댓글 (parent_comment_id FK)
post_likes            # 게시글 좋아요
post_bookmarks        # 게시글 북마크
comment_likes         # 댓글 좋아요

# 확장 & 트리거
CREATE EXTENSION IF NOT EXISTS pg_trgm
CREATE TRIGGER update_search_vector  # tsvector_update_trigger

# 인덱스
ix_board_posts_search_vector (GIN)
ix_board_posts_author_id
ix_board_posts_status
ix_board_posts_created_at
# ... 기타 외래키, 상태 인덱스
```

**마이그레이션 체인**:
```
base → 20260211_0001 (auth baseline)
     → 20260215_0002 (board system) ← HEAD
```

### ✅ Phase 8: 문서화

#### backend/doc/BOARD_API.md
- 18개 엔드포인트 상세 문서
- 요청/응답 JSON 예제
- 에러 코드 & 상태코드
- 레이트 제한 정보
- curl 예제 워크플로우
- DB 스키마 다이어그램
- 보안 고려사항

#### 최상위 doc/TASKS.md (업데이트)
- Phase 2.5 Board System 섹션 추가
- 7/7 완료 표시

---

## 파일 구조

```
app/domain/board/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── category.py           (BoardCategory)
│   ├── post.py               (BoardPost, PostStatus)
│   ├── comment.py            (Comment)
│   └── like_bookmark.py      (PostLike, PostBookmark, CommentLike)
├── schemas/
│   ├── __init__.py
│   ├── category.py           (Category schemas)
│   ├── post.py               (Post schemas)
│   └── comment.py            (Comment schemas + AuthorBrief)
└── services/
    ├── __init__.py
    ├── post_service.py       (PostService - 12개 메서드)
    └── comment_service.py    (CommentService - 8개 메서드)

app/api/v1/endpoints/board/
├── __init__.py               (board_router 조립)
├── categories.py             (4개 엔드포인트)
├── posts.py                  (6개 엔드포인트)
├── comments.py               (5개 엔드포인트)
└── reactions.py              (3개 엔드포인트)

alembic/versions/
└── 20260215_0002_board_system.py  (마이그레이션)

doc/
├── BOARD_API.md              (API 문서)
└── BOARD_IMPLEMENTATION_SUMMARY.md (이 파일)
```

---

## API 엔드포인트

### 요약 테이블

| 분류 | 엔드포인트 | 메서드 | 인증 | 상태 |
|------|----------|--------|------|------|
| **카테고리** | `/board/categories` | GET | 선택 | ✅ |
| | `/board/categories` | POST | 필수 | ✅ |
| | `/board/categories/{id}` | PUT | 필수 | ✅ |
| | `/board/categories/{id}` | DELETE | 필수 | ✅ |
| **게시글** | `/board/posts` | GET | 선택 | ✅ |
| | `/board/posts` | POST | 필수 | ✅ |
| | `/board/posts/{id}` | GET | 선택 | ✅ |
| | `/board/posts/{id}` | PUT | 필수 | ✅ |
| | `/board/posts/{id}` | DELETE | 필수 | ✅ |
| | `/board/search?q=` | GET | 선택 | ✅ |
| **댓글** | `/board/posts/{id}/comments` | GET | 선택 | ✅ |
| | `/board/posts/{id}/comments` | POST | 필수 | ✅ |
| | `/board/posts/{id}/comments/{cid}/replies` | POST | 필수 | ✅ |
| | `/board/comments/{id}` | PUT | 필수 | ✅ |
| | `/board/comments/{id}` | DELETE | 필수 | ✅ |
| **반응** | `/board/posts/{id}/like` | POST/DELETE | 필수 | ✅ |
| | `/board/posts/{id}/bookmark` | POST/DELETE | 필수 | ✅ |
| | `/board/comments/{id}/like` | POST/DELETE | 필수 | ✅ |

### 레이트 제한

| 작업 | 제한 | 시간 | 구현 |
|------|------|------|------|
| 게시글 작성 | 10개 | 1분 | Redis INCR ✅ |
| 댓글 작성 | 1개 | 1초 | Redis SETNX ✅ |

### 정렬 옵션 (게시글 목록)

- `recent` (기본): 최신순
- `popular`: 좋아요순
- `trending`: 좋아요+댓글수 합계순

### 검색 (게시글)

- **PRIMARY**: PostgreSQL Full-Text Search
  - `search_vector @@ plainto_tsquery('simple', q)`
  - GIN 인덱스 사용

- **FALLBACK**: 삼글자 유사도 (pg_trgm)
  - `similarity(title || ' ' || content, q) > 0.2`
  - 짧은 쿼리 대응

---

## 주요 기능

### 🔐 인증 & 권한

| 기능 | 요구사항 |
|------|---------|
| 공개 조회 (목록/상세/검색) | X-API-Key만 필요 |
| 인증 필요 작업 | X-API-Key + X-Platform + Authorization |
| 소유자 확인 | author_id == current_user.id |
| 관리자 작업 | 추후 권한 체크 추가 예정 |

### 💾 데이터 관리

| 기능 | 구현 |
|------|------|
| 소프트 삭제 | `is_deleted = True` |
| 삭제 마스킹 | 댓글은 `content = "[삭제됨]"` |
| 타임스탐프 | 자동 `created_at`, `updated_at` |
| UUID 기본키 | 모든 모델 |

### 🔢 통계

| 항목 | 추적 |
|------|------|
| 조회수 | `BoardPost.view_count` (GET 시 ++) |
| 좋아요 | `PostLike`, `PostBookmark`, `CommentLike` 테이블 |
| 댓글수 | `BoardPost.comment_count` (생성/삭제 시 ±) |
| 카운터 | 각 모델에 `*_count` 필드 |

### 📝 컨텐츠 처리

| 항목 | 방식 |
|------|------|
| HTML 새니타이제이션 | 정규식 기반 (bleach 없음) |
| 게시글 | 기본 포맷팅만 허용 (b, i, br, p) |
| 댓글 | 모든 HTML 태그 제거 |
| 위험 패턴 | script, iframe, onload= 등 제거 |

### 🌳 댓글 구조

```
게시글 (depth: null, post_id: uuid)
  ├── 댓글 1 (depth: 0, parent_comment_id: null)
  │   ├── 답댓글 1-1 (depth: 1, parent_comment_id: comment_id)
  │   └── 답댓글 1-2 (depth: 1, parent_comment_id: comment_id)
  └── 댓글 2 (depth: 0, parent_comment_id: null)
      └── 답댓글 2-1 (depth: 1, parent_comment_id: comment_id)
```

**제약:**
- 최대 2단계 (top-level + reply)
- depth >= 2는 생성 불가
- 트리 구조로 반환 (GET /posts/{id}/comments)

---

## 다음 단계

### 1️⃣ 마이그레이션 실행

```bash
# DB가 running 상태일 때
alembic upgrade head
```

**결과:**
- ✅ board_categories 테이블 생성
- ✅ board_posts 테이블 + search_vector 트리거
- ✅ comments 테이블
- ✅ post_likes, post_bookmarks, comment_likes
- ✅ pg_trgm 확장 활성화
- ✅ GIN 인덱스 생성

### 2️⃣ 앱 시작

```bash
uvicorn app.main:app --reload
```

**확인:**
- http://localhost:8000/docs (Swagger UI)
- /board 엔드포인트 모두 보이는지 확인

### 3️⃣ API 테스트

```bash
# 카테고리 생성
curl -X POST http://localhost:8000/api/v1/board/categories \
  -H "X-API-Key: your-key" \
  -H "X-Platform: web" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"name":"General","slug":"general"}'

# 게시글 조회
curl http://localhost:8000/api/v1/board/posts \
  -H "X-API-Key: your-key" \
  -H "X-Platform: web"

# 검색
curl "http://localhost:8000/api/v1/board/search?q=python" \
  -H "X-API-Key: your-key"
```

자세한 예제는 `doc/BOARD_API.md` 참고

### 4️⃣ 테스트 작성 (선택사항)

```bash
pytest tests/test_board_*.py -v
```

---

## 검증 체크리스트

### 코드 품질
- ✅ Python 문법 검증
- ✅ Import 에러 없음
- ✅ FastAPI 경고 해결
- ✅ Type hints 포함
- ✅ Docstrings 포함

### 구현 완료도
- ✅ 모델 (6개)
- ✅ 스키마 (Pydantic)
- ✅ 서비스 (20개 메서드)
- ✅ 엔드포인트 (18개)
- ✅ 이벤트 (10개)
- ✅ 마이그레이션
- ✅ 문서 (API + 구현)

### 아직 미실행
- ⏳ 마이그레이션 실행 (DB 필요)
- ⏳ API 실제 테스트 (앱 시작 필요)
- ⏳ 테스트 코드 작성

---

## 참고 링크

- **API 문서**: `doc/BOARD_API.md`
- **모델**: `app/domain/board/models/`
- **서비스**: `app/domain/board/services/`
- **엔드포인트**: `app/api/v1/endpoints/board/`
- **마이그레이션**: `alembic/versions/20260215_0002_board_system.py`

---

## 주의사항

1. **DB 연결**: 마이그레이션 전 PostgreSQL이 실행중이어야 함
2. **포트 확인**: .env에서 DB_PORT 확인 (기본: 5432)
3. **확장**: pg_trgm 확장은 마이그레이션에서 자동 생성
4. **검색**: 초기에는 tsvector가 비어있을 수 있음 (데이터 삽입 후 활성화)

---

**마지막 업데이트**: 2026-02-15
**상태**: ✅ 구현 완료, ⏳ 마이그레이션 실행 대기
