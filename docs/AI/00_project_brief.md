# AI/00 — 프로젝트 브리프

> 새 대화를 시작할 때 AI가 읽는 핵심 컨텍스트.

---

## 한 줄 요약

FastAPI 기반 SaaS 백엔드. DDD + 이벤트 드리븐 아키텍처로 소셜 인증(Google/Kakao/Naver), 실시간 채팅(WebSocket), 게시판, 블로그, FCM 푸시 알림을 제공하며, PostgreSQL/Redis/Firebase를 사용하고 GCP Cloud Run에 배포된다.

---

## 서비스 구성

| 컴포넌트 | 위치 | 역할 |
|---------|------|------|
| API Layer | `app/api/v1/endpoints/` | HTTP 요청/응답만 (비즈니스 로직 없음) |
| Domain: auth | `app/domain/auth/` | 소셜 로그인, JWT 발급, 사용자 관리 |
| Domain: chat | `app/domain/chat/` | 채팅방, 메시지, WebSocket 게이트웨이 |
| Domain: board | `app/domain/board/` | 게시판 CRUD, 댓글, 좋아요, 북마크 |
| Domain: blog | `app/domain/blog/` | 블로그 CRUD, 구독, 좋아요, 피드 |
| Domain: push | `app/domain/push/` | FCM 토큰 관리, 알림 목록/읽음, 이벤트 구독 |
| Domain: points | `app/domain/points/` | 포인트 적립/사용 (부분 구현) |
| Core | `app/core/` | DB, Redis, EventBus, FCM, OAuth 검증 |
| Middleware | `app/middleware/` | JWT 인증, Rate Limiting |

## 인프라 (외부 서비스, 건드리지 않음)

| 서비스 | 용도 | 환경변수 |
|--------|------|---------|
| PostgreSQL (asyncpg) | 주 데이터베이스 | `DATABASE_URL` |
| Redis | 세션, 캐시, Rate Limiting, CSRF 토큰 | `REDIS_URL` |
| Firebase Admin SDK | Google JWT 검증, FCM 발송 | `FIREBASE_CREDENTIALS_PATH` |
| GCP Cloud Run | 배포 환경 | — |

## 핵심 제약

1. **API Layer에 비즈니스 로직 작성 금지** → Service 위임만
2. **Domain 간 직접 import 금지** → EventBus를 통한 이벤트 통신만
3. **EventBus 이벤트 발행/구독 패턴 준수** → 도메인 경계 침범 금지
4. **모든 DB 쿼리는 async SQLAlchemy (`AsyncSession`)** → 동기 ORM 사용 금지
5. **환경변수 하드코딩 금지** → `app/core/config.py` (Pydantic BaseSettings)
6. **모든 변경은 docs/ R/D/I/V 동시 갱신**

## 코드 위치

```
app/
├── core/
│   ├── config.py           # Pydantic BaseSettings (환경변수)
│   ├── database.py         # AsyncEngine, get_db()
│   ├── cache.py            # Redis 클라이언트, get_cache()
│   ├── events.py           # EventBus (발행/구독)
│   ├── fcm.py              # Firebase Cloud Messaging
│   └── auth/               # OAuth 검증 (Google/Kakao/Naver)
├── domain/
│   ├── auth/               # models, schemas, services
│   ├── chat/               # models, schemas, services, handlers
│   ├── board/              # models, schemas, services, handlers
│   ├── blog/               # models, schemas, services, handlers
│   ├── push/               # models, schemas, services, handlers, fcm_service
│   └── points/             # models, schemas, services (부분 구현)
├── api/v1/endpoints/       # HTTP 계약 (auth, chat, board, blog, push)
├── middleware/             # rate_limit.py, auth.py (get_current_user)
├── migrations/             # Alembic 마이그레이션
└── main.py                 # FastAPI 앱 초기화만
```

## 현재 상태

- Auth (소셜 로그인 3플랫폼 + 보안 P1~P5): 완료 (76/76 테스트 통과)
- Chat (WebSocket, 1:1 방 dedup, 사용자 검색): 완료
- Board (CRUD, 댓글, 좋아요, 북마크): 완료
- Blog (CRUD, 구독, 좋아요, 피드): 완료
- Push (FCM, EventBus 구독): 완료
- 이벤트 드리븐 아키텍처: 47% 구현 (25/53 이벤트)
- 통합 테스트: 41/143 (29%)
- 배포 (GCP Cloud Run): 대기 중 (2026-03-20 목표)

## 이벤트 목록 (EventBus)

| 이벤트 이름 | 발행 도메인 | 구독 도메인 |
|------------|-----------|-----------|
| `board.post.created` | board | push |
| `board.comment.created` | board | push |
| `blog.post.created` | blog | push |
| `chat.message.received` | chat | push |
| `auth.user.registered` | auth | points |

## 알려진 기술 부채 (코드 작성 전 확인)

- CORS 설정 환경변수 기반으로 수정 필요 (C1)
- N+1 쿼리 (board posts 목록) → `selectinload()` 적용 필요 (C3)
- CSRF 검증 `hmac.compare_digest()` 적용 필요 (C4)
- Refresh Token 미구현 → 24시간 후 재로그인 필요
