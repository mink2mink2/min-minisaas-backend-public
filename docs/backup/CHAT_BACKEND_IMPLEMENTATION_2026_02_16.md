# Chat Backend 구현 완료 (2026-02-16)

## 📋 구현 요약

Chat MVP의 Backend 부분을 다음과 같이 완성했습니다:

### 1. 사용자 검색 API ✅

**파일**: `app/domain/auth/services/auth_service.py`, `app/api/v1/endpoints/users.py`

**구현 내용**:
- `GET /api/v1/users/search?q={query}`
- Query parameter: `q` (최소 2글자, 최대 100글자)
- 사용자명, 이메일, 실명으로 검색 가능
- 자신을 제외한 다른 사용자만 반환
- Response: `[{ id, name, picture, username, email }]`

**메서드**:
```python
# AuthService.search_users()
async def search_users(
    self,
    query: str,
    exclude_user_id: Optional[str] = None,
    limit: int = 10
) -> list
```

**특징**:
- SQL injection 방지 (ORM parameterized queries)
- 동적 쿼리 (조건 조합)
- 유효성 검증 (최소 글자 수)

---

### 2. 1:1 채팅 중복 생성 방지 ✅

**파일**: `app/domain/chat/services/chat_service.py`

**구현 내용**:
- `get_or_create_one_to_one_room()` 메서드 추가
- 같은 두 user_id 조합으로는 오직 1개의 room만 존재
- 이미 존재하면 기존 room_id 반환, 없으면 새로 생성

**메서드**:
```python
async def get_or_create_one_to_one_room(
    self,
    user_a_id: UUID,
    user_b_id: UUID
) -> ChatRoom
```

**동작 원리**:
1. 두 user_id를 정렬 (일관성)
2. is_group=False인 방 중에서 두 사용자가 모두 멤버인지 확인
3. 있으면 반환, 없으면 새로 생성

**DB 쿼리 최적화**:
- 기존 방 조회: 2개의 멤버십 확인
- 새 방 생성: 1회의 flush + 2개 멤버 insert

---

### 3. Room List 개선 (상대 정보 + 마지막 메시지) ✅

**파일**: `app/domain/chat/services/chat_service.py`

**구현 내용**:
- `list_rooms_with_details()` 메서드 추가
- 각 room마다 다음 정보 포함:
  - `participants`: 모든 참여자의 프로필 정보
  - `last_message`: 마지막 메시지 미리보기
  - `unread_count`: 읽지 않은 메시지 수 (향후)
  - `updated_at`: 방의 마지막 활동 시간

**Response 예시**:
```json
[
  {
    "room_id": "uuid",
    "name": "1:1 Chat",
    "is_group": false,
    "participants": [
      {
        "user_id": "uuid",
        "name": "John Doe",
        "picture": "https://...",
        "username": "johndoe"
      },
      {
        "user_id": "uuid",
        "name": "Jane Smith",
        "picture": "https://...",
        "username": "janesmith"
      }
    ],
    "last_message": {
      "content": "Hi there!",
      "sender_name": "John",
      "created_at": "2026-02-16T10:30:00"
    },
    "unread_count": 0,
    "updated_at": "2026-02-16T10:30:00"
  }
]
```

**쿼리 최적화**:
- N+1 문제 주의: 각 message, sender user 조회
- 향후 JOIN으로 최적화 가능

---

### 4. Chat Endpoint 업데이트 ✅

**파일**: `app/api/v1/endpoints/chat.py`

**변경 사항**:

#### GET /rooms (개선)
- 기존: 기본 room 정보만 반환
- 현재: `list_rooms_with_details()` 사용
  - 상대 정보
  - 마지막 메시지
  - unread_count

#### POST /rooms (1:1 정책 적용)
- `is_group=False` + `member_ids=[peer_id]` → `get_or_create_one_to_one_room()` 호출
- 그룹 채팅 → 기존 `create_room()` 호출
- 결과: 동일한 peer_id로 여러 번 요청해도 같은 room_id 반환

---

## 📋 API 스펙

### 사용자 검색
```
GET /api/v1/users/search?q=john&limit=10
Authorization: Bearer {token}
X-API-Key: {api_key}
X-Platform: mobile|web|desktop

Response (200):
[
  {
    "id": "uuid",
    "name": "John Doe",
    "picture": "https://...",
    "username": "johndoe",
    "email": "john@example.com"
  }
]

Error (400):
{ "detail": "Query too short (min 2 chars)" }
```

### 1:1 방 생성 (기존과 동일, 동작 개선)
```
POST /api/v1/chat/rooms
{
  "name": "",  // 1:1은 필수 아님 (UI에서 상대 이름 표시)
  "is_group": false,
  "member_ids": ["peer-uuid"]
}

Response (201):
{
  "id": "room-uuid",  // 기존 room_id 또는 새로 생성된 uuid
  "name": "1:1 Chat",
  "is_group": false,
  "created_by": "your-uuid",
  "member_count": 2,
  "created_at": "2026-02-16T10:00:00",
  "updated_at": "2026-02-16T10:00:00"
}
```

### Room List (개선)
```
GET /api/v1/chat/rooms?page=1&limit=20
Authorization: Bearer {token}
X-API-Key: {api_key}
X-Platform: mobile|web|desktop

Response (200):
{
  "items": [
    {
      "room_id": "uuid",
      "name": "상대 이름",
      "is_group": false,
      "participants": [{ "user_id", "name", "picture", "username" }],
      "last_message": { "content", "sender_name", "created_at" },
      "unread_count": 0,
      "updated_at": "2026-02-16T10:00:00"
    }
  ],
  "total": 5,
  "page": 1,
  "limit": 20,
  "pages": 1,
  "has_next": false,
  "has_prev": false
}
```

---

## 🔧 기술 상세

### 1:1 Room Dedup 로직

**DB 레벨**:
- `is_group=false`인 room만 대상
- 두 user_id를 정렬하여 일관성 유지
- 같은 정렬된 pair는 1개 room만 유지

**Application 레벨**:
```python
# 정렬된 user_id로 일관성 확보
user_ids = sorted([user_a_id, user_b_id])
user_1, user_2 = user_ids[0], user_ids[1]

# 기존 room 검색
# (is_group=False AND user_1 멤버 AND user_2 멤버)

# 없으면 새로 생성
```

**향후 개선**:
- DB UNIQUE constraint 추가: `UNIQUE(LEAST(user_1, user_2), GREATEST(user_1, user_2)) WHERE is_group=false`
- PostgreSQL 함수 사용으로 더 견고하게

---

### Room List 성능

**현재 구현**:
- Room 조회: O(1) 쿼리
- 각 room마다:
  - 참여자 정보: 1 쿼리
  - 마지막 메시지: 1 쿼리
  - 발신자 정보: 1 쿼리
- **총 쿼리**: 1 + 3N (N = room 수)

**향후 최적화**:
- JOIN으로 단일 쿼리로 통합
- LEFT JOIN으로 마지막 메시지까지 한 번에 조회
- 캐싱 (Redis): room_list:{user_id} - TTL 30초

---

## ✅ 검증 체크리스트

- [x] Python 컴파일 성공 (no syntax errors)
- [x] AuthService에 search_users 메서드 추가
- [x] ChatService에 get_or_create_one_to_one_room 메서드 추가
- [x] ChatService에 list_rooms_with_details 메서드 추가
- [x] users.py에 /search 엔드포인트 추가
- [x] chat.py의 /rooms GET 개선
- [x] chat.py의 /rooms POST에 1:1 정책 적용

---

## 📝 다음 단계

### Backend
- [ ] Unit test 작성 (test_chat_endpoints.py 확장)
- [ ] Integration test (create room → send message → list rooms)
- [ ] 성능 테스트 (1000개 room, 10000개 message)
- [ ] E2E 테스트 (App과 함께)

### App
- [ ] 사용자 검색 UI 구현
- [ ] Room 생성 시 search API 호출
- [ ] Room list에서 상대 정보 표시
- [ ] WS 재연결 로직 (exponential backoff)

---

## 📚 관련 파일

**수정된 파일**:
1. `app/domain/auth/services/auth_service.py` - search_users 메서드
2. `app/domain/chat/services/chat_service.py` - get_or_create_one_to_one_room, list_rooms_with_details
3. `app/api/v1/endpoints/users.py` - /search 엔드포인트
4. `app/api/v1/endpoints/chat.py` - /rooms GET/POST 개선

**생성된 문서**:
- `docs/CHAT_BACKEND_IMPLEMENTATION_2026_02_16.md` (현재 문서)

---

**작성일**: 2026-02-16
**상태**: ✅ Complete
**예상 App 구현 시간**: 4.5시간
