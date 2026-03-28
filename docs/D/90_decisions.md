# D/90 — 아키텍처 결정 기록 (Architecture Decision Records)

> ADR 형식: 상황(Context) → 결정(Decision) → 결과(Consequences)
> API나 아키텍처에 중요한 결정을 할 때마다 이 문서에 추가한다.

---

## ADR-001: FastAPI 선택 (vs Django, Flask)

**날짜**: 2026-02-01
**상태**: 수락됨

### 상황
백엔드 프레임워크를 선택해야 했다. 주요 후보는 FastAPI, Django, Flask였다.

### 고려된 대안

| 프레임워크 | 장점 | 단점 |
|-----------|------|------|
| **FastAPI** | 네이티브 비동기, 자동 OpenAPI 문서화, Pydantic 통합 | 생태계 규모 Django 대비 작음 |
| Django | 풍부한 ORM, Admin, 대규모 생태계 | 비동기 지원 후발주자, 과도한 설정 |
| Flask | 가볍고 유연 | 비동기 지원 미흡, 도구 직접 구성 필요 |

### 결정
**FastAPI를 선택한다.**

### 이유
- WebSocket 채팅에 비동기가 필수 (asyncio 네이티브 지원)
- Pydantic 기반 요청/응답 자동 검증
- OpenAPI 3.0 자동 생성으로 Flutter 팀과 API 계약 공유 용이
- 성능: Starlette 기반으로 Django 대비 2~3배 높은 처리량

### 결과
- ✅ 비동기 DB 쿼리, WebSocket, 외부 API 호출이 모두 일관된 async/await 패턴
- ✅ `POST /api/v1/auth/login/google` 등 API가 Swagger UI에서 자동 문서화
- ⚠️ Django Admin 없어 관리자 기능은 별도 구현 필요

---

## ADR-002: DDD + Event-driven 아키텍처 선택

**날짜**: 2026-02-01
**상태**: 수락됨

### 상황
프로젝트 초기 구조를 결정해야 했다. 간단한 MVC 구조 vs DDD 기반 레이어드 아키텍처.

### 결정
**DDD(Domain-Driven Design) + 레이어드 아키텍처 + Event-driven 패턴을 채택한다.**

도메인: auth, chat, board, blog, push, points를 독립된 경계 컨텍스트로 분리.

### 이유
- 기능이 6개 도메인으로 분리되어 있어 도메인 간 결합도가 낮아야 함
- 새 도메인(예: payments) 추가 시 기존 코드 수정 없이 가능
- 테스트 작성이 도메인별로 독립적으로 가능
- push 도메인이 다른 도메인의 이벤트에 반응하는 구조가 자연스러움

### 결과
- ✅ `domain/push/handlers.py`가 `board.post.created` 이벤트를 수신해 알림 발송
- ✅ board ↔ blog 직접 의존성 없음 (EventBus를 통한 간접 통신)
- ⚠️ 초기 설정 복잡도 증가
- ⚠️ 이벤트 흐름을 문서화하지 않으면 파악 어려움 → `D/10_architecture.md`에 이벤트 목록 유지

---

## ADR-003: Redis EventBus 패턴

**날짜**: 2026-02-05
**상태**: 수락됨

### 상황
도메인 간 이벤트 전달 메커니즘이 필요했다. 인프로세스 이벤트 버스 vs 외부 메시지 큐(Celery/RabbitMQ/Kafka).

### 결정
**인프로세스 EventBus (Redis Pub/Sub 백업) 패턴을 사용한다.**

단일 프로세스 내에서는 Python 딕셔너리 기반 핸들러 등록을 사용하고,
멀티 인스턴스 배포 시 Redis Pub/Sub로 이벤트를 전파한다.

### 이유
- DAU 10,000 수준에서 Kafka/RabbitMQ는 과도한 인프라
- Redis는 이미 캐싱 목적으로 사용 중 → 추가 인프라 없음
- 이벤트 처리 실패 시 재시도 로직은 MVP 이후 단계에서 추가

### 결과
- ✅ 추가 인프라 없이 이벤트 드리븐 패턴 구현
- ⚠️ 이벤트 영속성 없음 — 처리 실패 시 이벤트 소실 가능 (허용)
- ⚠️ 멀티 인스턴스 시 Redis Pub/Sub 연동 추가 구현 필요 (현재 단일 인스턴스)

---

## ADR-004: Firebase Admin SDK for FCM (vs 직접 FCM HTTP API)

**날짜**: 2026-02-10
**상태**: 수락됨

### 상황
FCM(Firebase Cloud Messaging) 발송 방법 선택.

### 결정
**Firebase Admin SDK를 사용한다.** (`firebase-admin` Python 패키지)

### 이유
- Google 공식 SDK로 인증 처리가 간단 (서비스 계정 JSON만 제공)
- 직접 HTTP API 사용 시 OAuth2 토큰 갱신을 수동 처리해야 함
- `messaging.send()` 한 줄로 Android/iOS 모두 처리
- Dry-run 모드로 토큰 유효성 테스트 가능

### 결과
- ✅ `domain/push/fcm_service.py`에서 SDK 사용으로 단순한 구현
- ✅ Google이 SDK 유지보수하므로 FCM API 변경에 자동 대응
- ⚠️ Firebase 프로젝트와 서비스 계정 키 관리 필요

---

## ADR-005: OAuth 서버사이드 검증 (보안)

**날짜**: 2026-02-01
**상태**: 수락됨

### 상황
OAuth 토큰 검증 위치 결정. 클라이언트(Flutter)에서만 검증 vs 서버에서 재검증.

### 결정
**클라이언트 토큰을 서버에서 OAuth 제공자에 재검증한다.**

- Google: Firebase Admin SDK `auth.verify_id_token(id_token)` 사용
- Kakao: `POST https://kapi.kakao.com/v2/user/me` (토큰으로 사용자 정보 요청)
- Naver: `GET https://openapi.naver.com/v1/nid/me` (토큰으로 사용자 정보 요청)

### 이유
- 클라이언트 시크릿(Client Secret)을 앱 번들에 포함하면 역공학으로 노출 가능
- 서버사이드 검증으로 토큰 위조/탈취 공격 방어
- 보안 표준 OWASP Mobile Top 10 대응

### 결과
- ✅ 클라이언트 시크릿이 서버에만 존재
- ✅ 소셜 로그인 토큰 위조 공격 차단
- ⚠️ Kakao, Naver 로그인 시 외부 API 호출 추가 지연 (~50-100ms)

---

## ADR-006: PostgreSQL + SQLAlchemy (vs NoSQL)

**날짜**: 2026-02-01
**상태**: 수락됨

### 상황
데이터베이스 선택. PostgreSQL vs MongoDB vs DynamoDB.

### 결정
**PostgreSQL 15+ + SQLAlchemy 2.0 (비동기) 를 사용한다.**

### 이유

| 기준 | PostgreSQL | MongoDB |
|------|-----------|---------|
| 관계형 데이터 | ✅ JOIN 최적화 | ⚠️ 임베딩 또는 Ref |
| ACID 트랜잭션 | ✅ 완전 지원 | ✅ v4.0+ |
| Full-text Search | ✅ tsvector | ✅ Atlas Search |
| 스키마 강제 | ✅ 마이그레이션 | ⚠️ Schemaless |
| 팀 익숙도 | ✅ 높음 | ⚠️ 중간 |

- 유저-게시글-댓글-좋아요 등 관계형 데이터가 중심
- 트랜잭션 무결성이 중요 (좋아요 카운트, 포인트)
- Alembic으로 마이그레이션 관리가 명확

### 결과
- ✅ `likes_count` 컬럼 원자적 업데이트로 동시성 문제 방지
- ✅ blog_subscriptions JOIN으로 피드 쿼리 최적화
- ⚠️ chat_messages 테이블이 대용량 성장 시 파티셔닝 고려 필요

---

## ADR-007: JWT 세션 전략

**날짜**: 2026-02-01
**상태**: 수락됨, 부분 구현

### 상황
인증 토큰 전략 결정. 세션 쿠키 vs JWT (액세스 토큰 + 리프레시 토큰).

### 결정
**HS256 서명 JWT를 사용한다. 액세스 토큰 만료: 24시간.**
리프레시 토큰은 향후 단계에서 추가한다.

### 이유
- Flutter 앱 — 쿠키보다 Authorization 헤더가 자연스러움
- Stateless — 서버 세션 저장소 불필요 (스케일 아웃 용이)
- 만료시간 24시간은 모바일 UX와 보안 균형점

### 현재 제한
- ⚠️ 리프레시 토큰 미구현 — 24시간 후 재로그인 필요
- ⚠️ 토큰 강제 만료(블랙리스트) 미구현 — 로그아웃 후 만료까지 토큰 유효

### 향후 개선
- Refresh Token (7일) + Redis 블랙리스트 구현 예정
- 관련 이슈: `POST /api/v1/auth/refresh` 엔드포인트 추가

---

## ADR-008: Event Publication Inconsistency - user.profile_updated

**날짜**: 2026-03-04
**상태**: 인식됨, 구현 예정
**심각도**: P0 (Critical)

### 상황
Task 7 (이벤트 드리븐 아키텍처 검증) 중 발견:
- `PUT /api/v1/users/me` 엔드포인트는 완전히 구현됨 (users.py:65-105)
- 하지만 프로필 업데이트 시 `user.profile_updated` 이벤트를 발행하지 않음

### 문제점
- **API 기능**: ✅ nickname, name, picture 업데이트 정상 작동
- **이벤트 발행**: ❌ EventBus에 `user.profile_updated` 퍼블리시 미구현
- **영향**: push 도메인이 프로필 변경 이벤트를 수신하지 못함
- **근본 원인**: 2026-03-04 nickname 기능 추가 시 API만 구현하고 이벤트는 미작업

### 결정
**`PUT /users/me` 엔드포인트에 `user.profile_updated` 이벤트 발행 로직을 추가한다.**

형식:
```python
await event_bus.publish("user.profile_updated", {
    "user_id": str(user_id),
    "fields": ["nickname", "name", "picture"],  # 실제 변경된 필드만
    "timestamp": datetime.utcnow()
})
```

### 이유
- ADR-002 (Event-driven 아키텍처)의 원칙 준수
- 도메인 간 느슨한 결합 유지 (push, notification 등 향후 구독자 가능)
- 이벤트 추적성/감시성 확보

### 결과 (예상)
- ✅ 프로필 변경 이벤트가 모든 리스너에 일관되게 전파
- ⚠️ 이벤트 구현율 계산 재검토 필요 (25→26이벤트 포함)

---

## ADR-009: 운영성 엔드포인트도 API Key 단독 보호에 의존하지 않는다

**날짜**: 2026-03-18
**상태**: 수락됨

### 상황
`POST /api/v1/verify/generate-daily/{date_str}`는 문서상 관리자용이지만 실제 구현은 `X-API-Key`만 요구하고 있었다.
앱 번들/클라이언트에서 API key가 노출될 수 있다는 전제를 두면, 운영성 작업을 API key 단독으로 보호하는 것은 보안 경계로 충분하지 않다.

### 결정
운영성 또는 관리자성 엔드포인트는 `X-API-Key`를 유지하더라도 반드시 다음 둘을 함께 적용한다.
- 사용자 인증 (`verify_any_platform` 또는 동등한 인증)
- 역할 검증 (`SUPERUSER_EMAILS` 기반 superuser 체크 또는 동등한 관리자 판별)

### 결과
- ✅ `generate_daily_ledger`는 더 이상 API key 단독 호출로 실행되지 않는다
- ✅ API key의 역할을 앱 식별/약한 필터로 제한하는 방향이 문서와 코드에서 일치한다
- ⚠️ 기존 엔드포인트 중 비슷한 패턴이 남아 있는지 지속 점검이 필요하다

---

## ADR-010: Alembic schema drift는 autogenerate보다 registry 보정 + 수동 migration으로 우선 대응한다

**날짜**: 2026-03-28
**상태**: 수락됨

### 상황
`alembic check` 수행 중 `blog_*` 및 `push_*` 테이블이 실제 DB에는 존재하지만 metadata에는 없는 것처럼 보이며 삭제 후보로 감지되는 문제가 있었다. 원인은 `app/db/model_registry.py`에 blog/push 모델 import가 누락되어 Alembic이 현재 모델 집합을 불완전하게 읽은 것이었다. 동시에 `fcm_tokens`는 `BaseModel.is_deleted`를 기대하지만 일부 DB 스키마에 해당 컬럼이 없는 drift도 확인되었다.

### 결정
- Alembic metadata 누락은 먼저 `app/db/model_registry.py`를 운영 DB 기준으로 보정한다.
- drift 보정은 `alembic revision --autogenerate` 대량 생성 대신, 필요한 컬럼만 다루는 수동 migration으로 우선 처리한다.
- 현재 baseline revision이 `Base.metadata.create_all()`에 의존하므로, autogenerate가 제안하는 drop/nullable/index 변경은 그대로 수용하지 않고 수동 검토한다.

### 결과
- ✅ `blog_*`, `push_*` 테이블이 삭제 후보로 오인되는 위험을 줄였다.
- ✅ `20260328_0012_fcm_tokens_basemodel_columns`로 개발/운영 DB에 동일한 보정 경로를 확보했다.
- ⚠️ baseline 설계 자체의 구조적 위험은 남아 있으므로, 신규 스키마 변경 시 registry 완전성 확인과 migration 수동 검토가 계속 필요하다.

---

## ADR-010: 앱 API에서 legacy auth 공개 진입점을 제거한다

**날짜**: 2026-03-18
**상태**: 수락됨

### 상황
앱은 Firebase/OAuth 기반 로그인 경로를 사용하고 있으며, 이메일+비밀번호 legacy auth는 실제 앱 코드 경로에서 사용되지 않았다.
반면 legacy auth는 공개 엔드포인트를 추가로 유지해 불필요한 공격면을 늘린다.

### 결정
`POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`를 앱 API에서 제거한다.

### 결과
- ✅ 불필요한 공개 인증 진입점 제거
- ✅ 앱 인증 경로를 모바일/OAuth 중심으로 단순화
- ⚠️ 이메일+비밀번호 인증이 다시 필요하면 별도 설계와 보안 검토 후 재도입해야 한다

---

## ADR-011: 앱 API는 X-API-Key + 실제 인증 조합을 기본값으로 한다

**날짜**: 2026-03-18
**상태**: 수락됨

### 상황
PDF 엔드포인트는 실제 사용자 인증만 적용되고, `users/{user_id}`는 공개 stub 상태였다.
웹 공개 API를 별도로 둘 계획이라면, 앱 API에서 공개/반공개 예외를 최소화하는 쪽이 더 안전하다.

### 결정
- PDF 엔드포인트는 `X-API-Key + verify_any_platform` 조합으로 강화한다.
- `GET /api/v1/users/{user_id}`는 공개로 두지 않고 인증 필요 엔드포인트로 전환한다.
- `X-API-Key`는 앱 식별/약한 필터로 문서화하되, 실제 보안 경계는 사용자 인증과 권한 검증으로 정의한다.

### 결과
- ✅ 앱 API 정책이 더 일관되고 예측 가능해진다
- ✅ 공개 프로필 stub, 인증-only 예외 같은 느슨한 구간이 줄어든다
- ⚠️ 공개 프로필/웹 전용 API는 별도 계약으로 다시 정의해야 한다

---

## ADR-012: board/blog 읽기 API도 앱 로그인 사용자 전용으로 본다

**날짜**: 2026-03-18
**상태**: 수락됨

### 상황
기존 board/blog 읽기 경로 일부는 `X-API-Key`만으로 접근 가능하거나 optional auth를 통해 로그인 사용자 컨텍스트만 덧붙이는 구조였다.
하지만 앱 번들에서 API key는 노출 가능한 값이므로, 이 방식은 외부 비로그인 클라이언트의 콘텐츠 수집을 충분히 막지 못한다.
또한 웹 공개 API는 별도 설계 대상으로 분리할 계획이다.

### 결정
- `GET /api/v1/board/posts`
- `GET /api/v1/board/posts/{post_id}`
- `GET /api/v1/board/posts/{post_id}/comments`
- `GET /api/v1/board/categories`
- `GET /api/v1/blog/categories`
- `GET /api/v1/blog/feed`
- `GET /api/v1/blog/users/{user_id}`
- `GET /api/v1/blog/posts/{post_id}`
- `GET /api/v1/blog/search`

위 읽기 경로를 모두 `X-API-Key + verify_any_platform` 필수 정책으로 전환한다.
단, 로그인된 사용자는 자신의 것뿐 아니라 다른 사용자의 콘텐츠도 조회할 수 있다.

### 결과
- ✅ 앱 외부에서 API key만으로 콘텐츠를 수집하는 경로가 줄어든다
- ✅ 앱 내부 UX는 유지하면서도 “로그인 사용자 전용 API”라는 경계가 명확해진다
- ⚠️ 향후 웹 공개 읽기 API가 필요하면 별도 경로/별도 계약으로 설계해야 한다

---

## ADR-013: ledger 검증 조회 API도 공개 예외로 두지 않는다

**날짜**: 2026-03-18
**상태**: 수락됨

### 상황
초기 ledger 설계에는 `GET /api/v1/verify/integrity/{date}`, `GET /api/v1/verify/root/{date}`, `GET /api/v1/verify/today`가 공개 검증 용도처럼 남아 있었다.
하지만 현재 제품 의도는 “누구나 공개 원장을 본다”가 아니라, 로그인한 사용자가 자신의 원장과 시스템 원장, 중간 원장, 최종 원장을 비교해 일관성을 확인하는 것이다.
또한 공개 조회는 웹 공개 API 전략과도 맞지 않는다.

### 결정
- `GET /api/v1/verify/integrity/{date}`
- `GET /api/v1/verify/root/{date}`
- `GET /api/v1/verify/today`

위 세 경로를 모두 `X-API-Key + verify_any_platform` 필수 정책으로 전환한다.
ledger 검증 API는 공개 검증 기능이 아니라 로그인 사용자 전용 검증 기능으로 정의한다.

### 결과
- ✅ ledger 도메인도 앱 API의 기본 보안 경계와 일관성을 갖는다
- ✅ 공개 원장이라는 표현에서 비롯되는 오해를 줄인다
- ⚠️ 향후 외부 공개 검증이 필요하면 별도 API 계약과 노출 범위를 다시 설계해야 한다

---

## ADR-014: rate limit은 엔드포인트별 중복 구현 대신 공통 모듈로 관리한다

**날짜**: 2026-03-18
**상태**: 수락됨

### 상황
기존 rate limit은 board 글/댓글, device 로그인 잠금, coin simulator 제어처럼 일부 경로에만 흩어져 있었다.
문서에는 전역 rate-limit 미들웨어가 있는 것처럼 적혀 있었지만, 실제 코드는 공통 모듈 없이 각 엔드포인트가 개별 구현을 갖고 있었다.
이 상태에서는 정책 누락, 429 형식 불일치, `Retry-After` 누락이 발생하기 쉽다.

### 결정
- 공통 rate-limit 로직은 `app/core/rate_limit.py`에서 관리한다.
- 라우터는 `enforce_ip_rate_limit`, `enforce_user_rate_limit` 같은 공통 헬퍼를 호출만 한다.
- 429 응답은 가능하면 `Retry-After` 헤더를 포함해 반환한다.
- 우선순위는 로그인 진입점과 쓰기/변경 API부터 적용하고, 읽기 API는 별도 단계로 확장한다.

### 결과
- ✅ 로그인/쓰기 API에 일관된 rate-limit 정책을 더 쉽게 적용할 수 있다
- ✅ 429 응답 형식과 헤더 정책을 공통화할 수 있다
- ⚠️ 아직 모든 조회 API까지 적용된 것은 아니므로 추가 점검이 필요하다

---

## ADR-015: logout도 account deletion과 동일하게 CSRF를 필수로 요구한다

**날짜**: 2026-03-18
**상태**: 수락됨

### 상황
기존 `POST /api/v1/auth/logout`은 CSRF 토큰이 있으면 검증하지만, 없어도 로그아웃을 진행했다.
반면 `DELETE /api/v1/auth/account`는 이미 CSRF를 필수로 요구하고 있었다.
세션/토큰 상태를 바꾸는 엔드포인트의 보호 수준이 서로 달라 정책 일관성이 부족했다.

### 결정
- `POST /api/v1/auth/logout`에도 `X-CSRF-Token`을 필수로 요구한다.
- logout과 account deletion은 동일한 CSRF 검증 경로를 사용한다.
- 클라이언트는 logout 전에 `GET /api/v1/auth/me`로 발급된 `csrf_token`을 함께 보낸다.

### 결과
- ✅ 인증 상태 변경 엔드포인트의 CSRF 정책이 일관된다
- ✅ 웹 세션 기반 경로뿐 아니라 공통 auth 경로 전체에서 보호 수준이 명확해진다
- ⚠️ logout 호출 클라이언트는 CSRF 토큰 전달 여부를 확인해야 한다

---

## ADR 추가 지침

새 아키텍처 결정이 필요할 때:
1. 이 파일에 `ADR-NNN: 제목` 형식으로 추가한다
2. 날짜, 상태, 상황, 결정, 이유, 결과를 명확히 기록한다
3. 관련된 코드 변경이 있으면 해당 파일 경로를 언급한다

---

## ADR-016: 표시용 식별자는 응답 계약에 명시적으로 포함한다

**날짜**: 2026-03-18
**상태**: 수락됨

### 상황
수동 검수 과정에서 채팅 메시지 하단과 board 댓글 작성자 영역에 UUID 같은 내부 식별자가 노출되는 문제가 발견되었다.
원인은 일부 응답 계약이 표시용 필드(`sender_name`, `nickname`)를 명시적으로 제공하지 않거나, 앱이 이를 받을 수 없는 형태로 축약되어 있었기 때문이다.

### 결정
- chat message 응답 계약에는 `sender_name`을 포함한다.
- board comment 작성자 요약 응답에는 `nickname`을 포함한다.
- 앱은 표시 이름이 필요한 영역에서 내부 ID 대신 `nickname -> name -> username -> id` 우선순위를 사용한다.

### 결과
- ✅ 앱 UI에서 내부 UUID가 사용자 표시 이름처럼 노출되는 문제를 줄인다
- ✅ 응답 계약이 “표시용 데이터”를 포함한다는 점이 명확해진다
- ⚠️ 향후 새 UI를 추가할 때도 ID와 표시 이름을 분리해 설계해야 한다
