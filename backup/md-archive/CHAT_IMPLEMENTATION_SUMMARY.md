# Chat Domain Implementation Summary

**Date:** 2026-02-15  
**Status:** Implemented (Backend MVP)

## Scope

채팅 기능을 기존 인증/게시판/PDF와 분리된 **독립 도메인**으로 추가했습니다.

- 모듈화: `app/domain/chat/*`
- 독립화: 기존 도메인 코드 직접 수정 최소화
- 이벤트드리븐: 메시지 생성/방 생성 시 EventBus 이벤트 발행 및 핸들러 처리

## Added Structure

### Domain (Chat)

- `app/domain/chat/models/room.py`
  - `ChatRoom`
  - `ChatRoomMember`
- `app/domain/chat/models/message.py`
  - `ChatMessage`
- `app/domain/chat/schemas/chat.py`
  - `ChatRoomCreate`, `ChatRoomResponse`
  - `ChatMessageCreate`, `ChatMessageResponse`
- `app/domain/chat/services/chat_service.py`
  - 채팅방 생성/목록
  - 메시지 전송/목록
  - 멤버십 검증
- `app/domain/chat/services/realtime_gateway.py`
  - 방 단위 WebSocket 연결 관리
- `app/domain/chat/services/chat_event_handlers.py`
  - `chat.room.created` 로깅
  - `chat.message.created` 브로드캐스트

### API

- `app/api/v1/endpoints/chat.py`
  - `GET /api/v1/chat/rooms`
  - `POST /api/v1/chat/rooms`
  - `GET /api/v1/chat/rooms/{room_id}/messages`
  - `POST /api/v1/chat/rooms/{room_id}/messages`
  - `WS /api/v1/chat/ws/rooms/{room_id}`

### Integration Points

- `app/api/v1/__init__.py`
  - chat router 등록
- `app/core/events.py`
  - `ChatRoomCreatedEvent`
  - `ChatMessageCreatedEvent`
- `app/main.py`
  - startup 시 `register_chat_event_handlers(event_bus)` 등록
- `app/db/model_registry.py`
  - Chat 모델 등록

## Migration

- `alembic/versions/20260215_0004_chat_domain.py`
  - `chat_rooms`
  - `chat_room_members`
  - `chat_messages`

## Compatibility / Safety

- 기존 auth/board/pdf 도메인 로직은 직접 변경하지 않음
- API 라우터에 chat만 추가
- 이벤트 기반으로 WS 브로드캐스트를 분리해 결합도 최소화

## Basic Verification

- Added: `tests/test_chat_endpoints.py`
  - OpenAPI에 chat route 등록 확인
  - 인증 헤더 누락 시 422 확인
- Test result: `3 passed`

## Next Work

1. E2E 테스트 추가 (room create -> send -> ws receive)
2. 읽음 상태/전달 상태 모델링
3. 메시지 수정/삭제 이벤트
4. 방 초대/강퇴 권한 정책
