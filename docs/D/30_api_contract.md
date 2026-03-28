# D/30 — API 계약 (API Contract)

> API가 변경될 때마다 이 문서를 먼저 갱신하고 코드를 수정한다.
> 앱(Flutter) 연동에 영향을 주는 변경은 `R/40_traceability.md`도 함께 갱신한다.

**Base URL**: `https://api.minisaas.com`
**API Version**: `v1`
**인증**: `Authorization: Bearer {jwt_token}` (별도 표기 없으면 필수)

**보안 경계 원칙**:
- `X-API-Key`는 앱 식별과 비인가 클라이언트 차단을 위한 약한 필터다.
- 실제 보안 경계는 사용자 인증(`verify_any_platform`)과 권한 검증이다.
- 이 백엔드는 앱/모바일 API를 우선 대상으로 하며, 웹 공개 API는 별도 설계 대상으로 본다.

---

## 공통 응답 형식

### 성공 응답
```json
// 단일 객체
{ "id": 1, "field": "value", ... }

// 목록
{ "items": [...], "total": 100, "skip": 0, "limit": 20 }
```

### 에러 응답
```json
{ "detail": "에러 메시지" }
// 또는 유효성 검사 오류
{ "detail": [{"loc": ["body", "field"], "msg": "field required", "type": "value_error"}] }
```

### 공통 HTTP 상태 코드

| 코드 | 의미 |
|------|------|
| 200 | 성공 (조회, 수정) |
| 201 | 생성 성공 |
| 204 | 삭제 성공 (응답 본문 없음) |
| 400 | 잘못된 요청 |
| 401 | 인증 실패 (토큰 없음/만료/위조) |
| 403 | 권한 없음 |
| 404 | 리소스 없음 |
| 409 | 충돌 (중복) |
| 422 | 유효성 검사 실패 |
| 429 | Rate Limit 초과 |
| 503 | 외부 서비스 오류 |

---

## AUTH 도메인 `/api/v1/auth`

### Removed legacy endpoints
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`

이메일+비밀번호 기반 legacy auth는 앱에서 사용하지 않아 제거되었다.
공통 플랫폼 refresh 엔드포인트 `POST /api/v1/auth/refresh`는 여전히 유지되며, `X-API-Key + X-Platform + 플랫폼별 인증 자격증명`이 필요하다.
앱 인증 진입점은 `/auth/login/mobile`, `/auth/login/kakao`, `/auth/login/naver`를 사용한다.

### POST /api/v1/auth/login/google
Google Firebase ID Token으로 로그인하고 JWT를 발급받는다.

**인증**: 불필요

**Request Body**:
```json
{
  "id_token": "eyJhbGci..."  // Firebase ID Token
}
```

**Response 200**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "nickname": "홍길동",
    "provider": "google",
    "profile_image": "https://...",
    "created_at": "2026-02-01T00:00:00Z"
  }
}
```

**에러**:
- `401` — 유효하지 않거나 만료된 Firebase ID Token

---

### POST /api/v1/auth/login/kakao
Kakao Access Token으로 로그인한다. 서버에서 카카오 API를 통해 검증한다.

**인증**: 불필요

**Request Body**:
```json
{
  "access_token": "kakao_access_token_here"
}
```

**Response 200**: (Google 로그인과 동일 구조, `"provider": "kakao"`)

**에러**:
- `401` — 유효하지 않은 카카오 토큰
- `503` — 카카오 API 서버 오류

---

### POST /api/v1/auth/login/naver
Naver Access Token으로 로그인한다. 서버에서 네이버 API를 통해 검증한다.

**인증**: 불필요

**Request Body**:
```json
{
  "access_token": "naver_access_token_here"
}
```

**Response 200**: (Google 로그인과 동일 구조, `"provider": "naver"`)

---

### POST /api/v1/auth/logout
현재 기기에서 로그아웃한다. FCM 토큰을 비활성화한다.

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 + `X-CSRF-Token` 필수

**정책**:
- `GET /api/v1/auth/me`에서 발급된 `csrf_token`을 함께 보내야 한다.
- logout은 더 이상 CSRF 선택 검증이 아니다.

**Request Body**:
```json
{
  "fcm_token": "fcm_token_to_deactivate"  // 선택
}
```

**Response 200**:
```json
{ "message": "Successfully logged out" }
```

**에러**:
- `403` — `X-CSRF-Token` 누락 또는 만료/불일치

---

### GET /api/v1/auth/me
현재 로그인된 사용자 정보를 반환한다.

**Response 200**:
```json
{
  "id": 1,
  "email": "user@gmail.com",
  "nickname": "홍길동",
  "provider": "google",
  "profile_image": "https://...",
  "is_admin": false,
  "created_at": "2026-02-01T00:00:00Z"
}
```

---

## CHAT 도메인 `/api/v1/chat`

### GET /api/v1/chat/rooms
내가 참여 중인 채팅방 목록을 최신 메시지 순으로 반환한다.

**Response 200**:
```json
{
  "items": [
    {
      "id": 1,
      "type": "direct",
      "participants": [
        { "id": 2, "nickname": "김철수", "profile_image": "https://..." }
      ],
      "last_message": {
        "content": "안녕하세요",
        "sender_id": 2,
        "created_at": "2026-03-01T12:00:00Z"
      },
      "unread_count": 3,
      "created_at": "2026-02-15T10:00:00Z"
    }
  ]
}
```

---

### POST /api/v1/chat/rooms
1:1 채팅방을 생성한다. 이미 존재하면 기존 채팅방을 반환한다.

**Request Body**:
```json
{
  "target_user_id": 2  // 상대방 사용자 ID
}
```

**Response 201** (신규) / **200** (기존):
```json
{
  "id": 1,
  "type": "direct",
  "participants": [...],
  "created_at": "2026-02-15T10:00:00Z"
}
```

**에러**:
- `400` — 자기 자신과 채팅방 생성 시도
- `404` — target_user_id 사용자 없음

---

### GET /api/v1/chat/rooms/{room_id}/messages
채팅방의 메시지 이력을 페이지네이션으로 반환한다.

**Path Params**: `room_id` (integer)
**Query Params**: `skip=0`, `limit=50`

**Response 200**:
```json
{
  "items": [
    {
      "id": 100,
      "room_id": 1,
      "sender_id": 1,
      "sender_name": "홍길동",
      "content": "안녕하세요",
      "message_type": "text",
      "created_at": "2026-03-01T12:00:00Z"
    }
  ],
  "total": 250,
  "skip": 0,
  "limit": 50
}
```

**에러**: `403` — 채팅방 참여자가 아님

---

### POST /api/v1/chat/rooms/{room_id}/messages
HTTP를 통해 메시지를 전송한다 (WebSocket 폴백).

**Request Body**:
```json
{
  "content": "안녕하세요",
  "message_type": "text"
}
```

**Response 201**:
```json
{
  "id": 101,
  "room_id": 1,
  "sender_id": 1,
  "content": "안녕하세요",
  "created_at": "2026-03-01T12:01:00Z"
}
```

---

## COIN SIMULATOR 도메인 `/api/v1/coin-simulator`

### GET /api/v1/coin-simulator/dashboard
시뮬레이터 상태/자산/포지션/최근 거래를 조회한다.
Cloud Run API는 Redis 캐시를 우선 사용하고, 캐시 미스 시 로컬 코인 서버 API에서 최신 스냅샷을 가져온다.

### POST /api/v1/coin-simulator/start
superuser만 시뮬레이터를 시작할 수 있다.
Cloud Run API가 로컬 코인 서버의 `/api/bot/start`를 호출한 뒤 캐시를 갱신한다.

### POST /api/v1/coin-simulator/stop
superuser만 시뮬레이터를 중지할 수 있다.
Cloud Run API가 로컬 코인 서버의 `/api/bot/stop`을 호출한 뒤 캐시를 갱신한다.

### PUT /api/v1/coin-simulator/settings
superuser만 시뮬레이터 설정을 변경할 수 있다.
Cloud Run API가 로컬 코인 서버의 전략 설정 API를 호출한 뒤 캐시를 갱신한다.

**Request Body**:
```json
{
  "mode": "paper",
  "exchange": "binance",
  "refresh_interval_seconds": 5,
  "analysis_limit": 30,
  "default_order_amount": 100.0,
  "risk_per_trade_pct": 1.0,
  "auto_stop_loss_pct": 2.0,
  "auto_take_profit_pct": 3.0,
  "enabled_strategies": ["bb_strategy"]
}
```

---

## LEDGER 도메인 `/api/v1/verify`

### GET /api/v1/verify/my-chain
내 거래 체인 무결성을 검증한다.

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 필수

---

### GET /api/v1/verify/my-transactions
내 거래 내역과 해시 체인을 조회한다.

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 필수

---

### GET /api/v1/verify/integrity/{date_str}
특정 날짜의 시스템 원장 무결성을 검증한다.

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 필수
**정책**:
- 공개 검증 엔드포인트로 두지 않는다.
- 로그인한 사용자가 자신의 원장과 시스템 원장을 대조하는 용도로 사용한다.

---

### GET /api/v1/verify/root/{date_str}
특정 날짜의 시스템 원장 루트를 조회한다.

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 필수
**정책**:
- 공개 조회를 허용하지 않는다.
- 로그인한 사용자가 자신의 원장과 같은 날짜의 시스템 원장을 비교하는 용도로 사용한다.

---

### GET /api/v1/verify/today
오늘 날짜의 시스템 원장 루트를 조회한다.

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 필수

---

### POST /api/v1/verify/generate-daily/{date_str}
일일 시스템 원장을 생성한다.

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 필수
**권한**: superuser만 가능

**Path Params**:
- `date_str` — `YYYY-MM-DD`

**Response 200**:
```json
{
  "status": "success",
  "date": "2026-03-18",
  "system_hash": "abc123",
  "transaction_count": 24,
  "user_count": 7
}
```

**에러**:
- `400` — 날짜 형식 오류
- `401` — 인증 실패
- `403` — 관리자 권한 없음
- `500` — 원장 생성 실패

---

### WS /api/v1/chat/ws/rooms/{room_id}
실시간 채팅 WebSocket 연결.

**연결 URL**: `wss://api.minisaas.com/api/v1/chat/ws/rooms/{room_id}?token={jwt_token}`

**수신 메시지 형식**:
```json
{
  "type": "message",
  "data": {
    "id": 101,
    "sender_id": 2,
    "sender_nickname": "김철수",
    "content": "안녕하세요",
    "created_at": "2026-03-01T12:01:00Z"
  }
}
```

**전송 메시지 형식**:
```json
{
  "content": "반갑습니다",
  "message_type": "text"
}
```

**연결 거부**: 토큰 없음/만료 시 WebSocket 코드 `4001`로 연결 거부

---

## BOARD 도메인 `/api/v1/board`

### GET /api/v1/board/posts
게시글 목록 조회.

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 필수
**정책**:
- 앱 로그인 사용자만 조회할 수 있다.
- 타인 게시글 조회는 허용한다.
- `is_liked`, `is_bookmarked`는 로그인 사용자 기준으로 항상 계산된다.
**Query Params**: `skip=0`, `limit=20`, `category=string`, `search=string`, `sort=latest|popular`

**Response 200**:
```json
{
  "items": [
    {
      "id": 1,
      "title": "첫 번째 게시글",
      "content": "내용 미리보기...",
      "author": { "id": 1, "nickname": "홍길동" },
      "category": "자유",
      "tags": ["개발", "FastAPI"],
      "likes_count": 10,
      "comments_count": 5,
      "view_count": 100,
      "my_reaction": { "liked": true, "bookmarked": false },
      "created_at": "2026-02-20T09:00:00Z"
    }
  ],
  "total": 150,
  "skip": 0,
  "limit": 20
}
```

---

### POST /api/v1/board/posts
게시글 작성.

**Request Body**:
```json
{
  "title": "제목 (최대 255자)",
  "content": "내용",
  "category": "자유",
  "tags": ["개발", "FastAPI"]
}
```

**Response 201**: 생성된 게시글 (위 목록 아이템과 동일 구조)

**Rate Limit**: 10개/분

---

### GET /api/v1/board/posts/{id}
게시글 상세 조회.

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 필수
**정책**:
- 앱 로그인 사용자만 조회할 수 있다.
- 타인 게시글 상세 조회는 허용한다.

**Response 200**: 목록 아이템과 동일 구조 (전체 내용 포함)

**에러**: `404` — 존재하지 않거나 삭제된 게시글

---

## PDF 도메인 `/api/v1/pdf`

모든 PDF 엔드포인트는 `X-API-Key + X-Platform + 플랫폼별 인증 자격증명`이 필요하다.
즉 정책은 `앱 식별 + 실제 사용자 인증`이다.

### POST /api/v1/pdf/upload
PDF 업로드.

### POST /api/v1/pdf/{file_id}/convert
PDF 변환 요청.

### GET /api/v1/pdf/{file_id}/status
변환 상태 조회.

### GET /api/v1/pdf/user/files
내 PDF 파일 목록 조회.

### GET /api/v1/pdf/{file_id}
내 PDF 파일 상세 조회.

### GET /api/v1/pdf/{file_id}/download
변환된 CSV 다운로드.

### DELETE /api/v1/pdf/{file_id}
내 PDF 파일 삭제.

---

## USERS 도메인 `/api/v1/users`

### GET /api/v1/users/{user_id}
다른 사용자 프로필 조회용 자리표시자 엔드포인트.

**인증**: `X-API-Key + X-Platform + 플랫폼별 인증 자격증명` 필수

공개 프로필 API로 열어두지 않으며, 향후 공개 정책이 필요하면 별도 계약으로 재설계한다.

---

### PUT /api/v1/board/posts/{id}
게시글 수정 (본인만).

**Request Body**:
```json
{
  "title": "수정된 제목",
  "content": "수정된 내용",
  "category": "개발",
  "tags": ["Python"]
}
```

**Response 200**: 수정된 게시글
**에러**: `403` — 본인 게시글이 아님

---

### DELETE /api/v1/board/posts/{id}
게시글 삭제 (본인 또는 관리자). 소프트 삭제.

**Response 204** (본문 없음)

---

### POST /api/v1/board/posts/{id}/like
게시글 좋아요.

**Response 201**:
```json
{ "likes_count": 11 }
```

**에러**: `409` — 이미 좋아요 함

---

### DELETE /api/v1/board/posts/{id}/like
게시글 좋아요 취소.

**Response 200**:
```json
{ "likes_count": 10 }
```

---

### POST /api/v1/board/posts/{id}/bookmark
게시글 북마크.

**Response 201**: `{ "message": "Bookmarked" }`
**에러**: `409` — 이미 북마크 함

---

### DELETE /api/v1/board/posts/{id}/bookmark
북마크 취소.

**Response 204**

---

### GET /api/v1/board/posts/{id}/comments
댓글 목록 조회.

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 필수

**Query Params**: `skip=0`, `limit=50`

**Response 200**:
```json
{
  "items": [
    {
      "id": 1,
      "content": "좋은 글이네요",
      "author": { "id": 2, "nickname": "김철수" },
      "parent_id": null,
      "created_at": "2026-02-20T10:00:00Z"
    }
  ]
}
```

---

### POST /api/v1/board/posts/{id}/comments
댓글 작성.

**Request Body**:
```json
{
  "content": "댓글 내용",
  "parent_id": null  // 대댓글이면 부모 댓글 ID
}
```

**Response 201**: 생성된 댓글
**Rate Limit**: 1개/초

---

### DELETE /api/v1/board/comments/{id}
댓글 삭제 (본인 또는 관리자). 소프트 삭제.

**Response 204**

---

## BLOG 도메인 `/api/v1/blog`

### GET /api/v1/blog/feed
내가 구독한 블로거들의 최신 글 피드.

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 필수

**Query Params**: `skip=0`, `limit=20`

**Response 200**:
```json
{
  "items": [
    {
      "id": 1,
      "title": "FastAPI 심층 분석",
      "content": "미리보기...",
      "slug": "fastapi-deep-dive",
      "author": { "id": 3, "nickname": "이개발" },
      "category": "개발",
      "likes_count": 25,
      "view_count": 500,
      "my_liked": false,
      "created_at": "2026-03-01T08:00:00Z"
    }
  ]
}
```

---

### GET /api/v1/blog/categories
블로그 카테고리 목록 조회.

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 필수

---

### GET /api/v1/blog/search
블로그 게시글 검색/목록 조회.

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 필수
**정책**:
- 앱 로그인 사용자만 조회할 수 있다.
- 타인 게시글 검색/열람은 허용한다.
**Query Params**: `query=string`, `category=string`, `skip=0`, `limit=20`

**Response 200**: 피드와 동일 구조

---

### POST /api/v1/blog/posts
블로그 게시글 작성.

**Request Body**:
```json
{
  "title": "제목",
  "content": "마크다운 내용",
  "category": "개발",
  "tags": ["Python", "FastAPI"],
  "is_published": true
}
```

**Response 201**: 생성된 블로그 포스트

---

### GET /api/v1/blog/users/{user_id}
특정 사용자의 블로그 게시글 목록 조회.

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 필수
**정책**:
- 앱 로그인 사용자만 조회할 수 있다.
- 타인 블로그 조회는 허용한다.

**Response 200**: 피드와 동일 구조

---

### GET /api/v1/blog/posts/{id}
블로그 게시글 상세 (조회수 증가).

**인증**: `X-API-Key` + `X-Platform` + 플랫폼별 인증 자격증명 필수

**Response 200**: 전체 내용 포함한 블로그 포스트

---

### PUT /api/v1/blog/posts/{id}
블로그 수정 (본인만).

**Request Body**: POST와 동일
**Response 200**: 수정된 게시글

---

### DELETE /api/v1/blog/posts/{id}
블로그 삭제 (본인만).

**Response 204**

---

### POST /api/v1/blog/posts/{id}/like
블로그 좋아요.

**Response 201**: `{ "likes_count": 26 }`
**에러**: `409`

---

### DELETE /api/v1/blog/posts/{id}/like
블로그 좋아요 취소.

**Response 200**: `{ "likes_count": 25 }`

---

### POST /api/v1/blog/subscribe/{id}
블로거 구독. `{id}`는 블로그 포스트 ID가 아닌 **작성자(user) ID**.

**Response 201**: `{ "message": "Subscribed" }`
**에러**: `409` — 이미 구독, `400` — 자기 자신 구독

---

### DELETE /api/v1/blog/subscribe/{id}
구독 취소.

**Response 204**

---

## PUSH 도메인 `/api/v1/push`

### POST /api/v1/push/tokens
FCM 토큰 등록. 이미 존재하면 갱신.

**Request Body**:
```json
{
  "token": "fcm_registration_token",
  "platform": "android"  // "ios" 또는 "android"
}
```

**Response 201** (신규) / **200** (기존 갱신):
```json
{
  "id": 1,
  "token": "fcm_registration_token",
  "platform": "android",
  "active": true,
  "created_at": "2026-03-01T00:00:00Z"
}
```

---

### PUT /api/v1/push/tokens/{id}
FCM 토큰 갱신.

**Request Body**:
```json
{
  "platform": "ios",
  "device_name": "iPhone 15 Pro"
}
```

**Response 200**: 갱신된 토큰 레코드

**비고**:
- `{id}` 는 `fcm_tokens.id` UUID
- 토큰 문자열 자체를 교체하지 않고 플랫폼/디바이스 메타데이터를 갱신한다

---

### DELETE /api/v1/push/tokens/{token}
FCM 토큰 삭제 (로그아웃 시).

**Response 204**

**비고**:
- 현재 인증된 사용자 소유 토큰만 삭제 가능
- 다른 사용자의 토큰 문자열을 전달해도 삭제되지 않는다

---

### GET /api/v1/push/notifications
내 알림 목록.

**Query Params**: `page=1`, `limit=20`

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid-notification-id",
      "title": "새 댓글",
      "body": "홍길동님이 댓글을 남겼습니다.",
      "event_type": "board.comment.created",
      "related_id": "uuid-post-id",
      "is_read": false,
      "created_at": "2026-03-01T12:00:00Z",
      "sent_at": "2026-03-01T12:00:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "limit": 20,
  "has_next_page": false
}
```

---

### GET /api/v1/push/notifications/unread/count
읽지 않은 알림 수.

**Response 200**:
```json
{ "unread_count": 5 }
```

---

### PUT /api/v1/push/notifications/{id}/read
특정 알림 읽음 처리.

**Response 200**:
```json
{ "read": true }
```

**에러**: `404` — 내 알림이 아니거나 존재하지 않음

---

### PUT /api/v1/push/notifications/read-all
모든 알림 읽음 처리.

**Response 200**:
```json
{ "marked_count": 5 }
```

---

### DELETE /api/v1/push/notifications/{id}
알림 삭제.

**Response 204**
**에러**: `404` — 내 알림이 아니거나 존재하지 않음

---

## 헬스체크

### GET /health
서비스 상태 확인.

**인증**: 불필요

**Response 200**:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2026-03-03T00:00:00Z"
}
```

**Response 503**: DB 또는 Redis 연결 실패 시

---

## API 변경 이력

| 날짜 | 변경 내용 | 영향 |
|------|----------|------|
| 2026-02-11 | Auth, Chat API 최초 구현 | - |
| 2026-02-15 | Board API 추가 | Flutter Board 화면 |
| 2026-02-20 | Blog API 추가 | Flutter Blog 화면 |
| 2026-02-25 | Push API 추가 | Flutter 알림 화면 |
| 2026-03-01 | unread/count 엔드포인트 추가 | 앱 탭바 뱃지 |
| 2026-03-18 | legacy auth 제거, board/blog 읽기 인증 필수화, PDF/Users 보호 강화 | 앱은 기존 인증 헤더 유지, 외부 비로그인 조회 차단 |
| 2026-03-18 | chat message 응답에 `sender_name` 추가, board comment 작성자에 `nickname` 포함 | 앱 채팅/댓글 표시명이 내부 ID 대신 닉네임/이름 우선으로 표시됨 |
