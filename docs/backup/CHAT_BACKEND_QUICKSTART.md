# Chat Backend Quick Start (for AI/Dev)

## Core Endpoints
- `GET /api/v1/chat/rooms`
- `POST /api/v1/chat/rooms`
- `GET /api/v1/chat/rooms/{room_id}/messages`
- `POST /api/v1/chat/rooms/{room_id}/messages`
- `WS  /api/v1/chat/ws/rooms/{room_id}`

## Required Headers
- `X-API-Key`
- `X-Platform`
- `Authorization: Bearer ...` (web은 session cookie)

## Member Model
- 연결 기준은 `chat_room_members`
- room 참여자는 `member_ids + creator_id`
- 클라이언트는 상대 `user_id(UUID)`를 알아야 실제 다자/1:1 채팅 가능

## Immediate TODO for MVP
1. `users` 검색 API 추가 (`/users/search?q=`)
2. 1:1 room unique policy(두 user 조합 고유)
3. room list 응답에 상대 요약 정보 포함
4. WS auth 정책을 web/mobile/desktop 일관화
