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

## ADR 추가 지침

새 아키텍처 결정이 필요할 때:
1. 이 파일에 `ADR-NNN: 제목` 형식으로 추가한다
2. 날짜, 상태, 상황, 결정, 이유, 결과를 명확히 기록한다
3. 관련된 코드 변경이 있으면 해당 파일 경로를 언급한다
