# R/30 — 비기능 요구사항 (Non-Functional Requirements)

---

## 1. 성능 (Performance)

### 응답시간 목표

| 지표 | 목표값 | 측정 방법 |
|------|--------|----------|
| 평균 응답시간 (avg) | **< 100ms** | APM 수집 평균값 |
| 95th percentile | **< 500ms** | APM p95 |
| 99th percentile | **< 1,000ms** | APM p99 |
| WebSocket 메시지 지연 | **< 50ms** | 클라이언트-서버 왕복 |

### 처리량 목표

| 지표 | 목표값 |
|------|--------|
| 초당 요청 처리 (RPS) | 500+ RPS (피크) |
| 일간 활성 사용자 (DAU) | 10,000명 |
| 동시 접속자 | 1,000+ (WebSocket 포함) |
| DB 연결 풀 | 최소 20개, 최대 100개 |

### 성능 최적화 전략

- **Redis 캐싱**: 자주 조회되는 데이터 (게시글 목록, 블로그 피드) 캐싱
- **데이터베이스 인덱싱**: 자주 필터링되는 컬럼에 인덱스 적용
  - `board_posts.author_id`, `board_posts.category`, `board_posts.created_at`
  - `chat_messages.room_id`, `chat_messages.created_at`
  - `push_notifications.user_id`, `push_notifications.read`
- **SQLAlchemy Connection Pooling**: `pool_size=20`, `max_overflow=80` 설정
- **비동기 처리**: 모든 DB 쿼리 및 외부 API 호출을 `async/await`로 처리
- **N+1 쿼리 방지**: `selectinload` / `joinedload` 활용

---

## 2. 가용성 (Availability)

| 지표 | 목표값 | 계산 |
|------|--------|------|
| 가용성 (Uptime) | **99.9%** | 월 최대 43분 다운타임 허용 |
| RTO (복구 시간 목표) | **< 5분** | 서비스 장애 발생 후 복구까지 시간 |
| RPO (복구 시점 목표) | **< 1시간** | 최대 1시간 데이터 손실 허용 |

### 고가용성 전략

- **다중 인스턴스**: GCP Cloud Run 최소 인스턴스 2개 이상 유지
- **자동 스케일링**: CPU 70% 기준 자동 스케일 아웃
- **헬스체크**: `/health` 엔드포인트 30초 간격 모니터링
- **데이터베이스 이중화**: Cloud SQL HA 구성 (Primary + Standby)
- **Redis 이중화**: Memorystore 복제본 구성

---

## 3. 보안 (Security)

### 인증/인가

| 요구사항 | 구현 방식 |
|---------|----------|
| JWT 기반 인증 | HS256 알고리즘, 만료시간 24시간 |
| OAuth 서버사이드 검증 | 클라이언트 토큰을 서버에서 OAuth 제공자에 재검증 |
| 권한 기반 접근 제어 | FastAPI `Depends(get_current_user)` + 리소스 소유자 확인 |
| 토큰 갱신 | Refresh Token 패턴 (향후 구현) |

### Rate Limiting

| 엔드포인트 유형 | 제한 |
|---------------|------|
| 공개 엔드포인트 기본 | 60 req/min per IP |
| 로그인 엔드포인트 | 10 req/min per IP |
| 게시글 작성 | 10개/min per user |
| 댓글 작성 | 1개/sec per user |
| WebSocket 연결 | 5개/user |

### 데이터 보안

- **HTTPS 전용**: 모든 통신 TLS 1.2+ 필수
- **민감정보 로그 금지**: 토큰, DB URL, API 키 로그 출력 금지
- **SQL Injection 방지**: SQLAlchemy ORM 사용, raw SQL 최소화
- **XSS 방지**: Pydantic 스키마 자동 이스케이핑
- **CORS 설정**: 허용된 Origin만 접근 가능
- **Production에서 Swagger 비활성화**: `/docs`, `/redoc` 접근 차단

---

## 4. 확장성 (Scalability)

### 수평 확장 (Horizontal Scaling)

- **Stateless API 서버**: 세션 상태를 서버 메모리에 저장하지 않음
- **Redis 기반 세션/캐시**: 모든 인스턴스가 공유 상태 접근
- **EventBus via Redis**: 멀티 인스턴스 간 이벤트 전파

### 데이터 확장

| 테이블 | 예상 레코드 수 (1년) | 대응 전략 |
|--------|------------------|----------|
| `chat_messages` | 100M+ | 파티셔닝 (created_at 기준) |
| `push_notifications` | 50M+ | 오래된 알림 주기적 아카이브 |
| `board_posts` | 1M+ | 인덱스 최적화 |

### 캐싱 전략

```
[Client] → [API Server] → [Redis Cache] → [PostgreSQL]
                           ↑
                    Cache Hit: 직접 반환
                    Cache Miss: DB 조회 후 캐싱
```

- 블로그 피드: TTL 5분
- 게시글 목록: TTL 1분
- 사용자 정보: TTL 10분

---

## 5. 유지보수성 (Maintainability)

| 요구사항 | 기준 |
|---------|------|
| 코드 테스트 커버리지 | 목표 80% 이상 |
| 문서화 | API 엔드포인트 100% OpenAPI 문서화 |
| 코드 스타일 | Black, isort, Ruff 린터 통과 필수 |
| 타입 힌트 | 모든 함수에 타입 힌트 필수 |
| 로그 구조화 | JSON 형식 로그, 추적 ID 포함 |

---

## 6. 동시성 (Concurrency)

| 시나리오 | 목표 |
|---------|------|
| 동시 WebSocket 연결 | 1,000+ |
| 동시 REST API 요청 | 500+ |
| DB 동시 쿼리 | 100+ (Connection Pool) |
| 이벤트 처리 동시성 | 비동기 이벤트 핸들러 |

### WebSocket 동시성 전략

- `asyncio` 기반 비동기 WebSocket 핸들링
- Redis Pub/Sub로 멀티 인스턴스 간 메시지 전파
- 연결 풀 관리로 메모리 효율화

---

## 7. 관찰성 (Observability)

| 요구사항 | 도구/방법 |
|---------|----------|
| 구조화된 로깅 | Python logging + JSON formatter |
| 분산 추적 | Request ID 헤더 전파 |
| 메트릭 수집 | Prometheus + Grafana (선택사항) |
| 에러 추적 | Sentry (선택사항) |
| 헬스체크 | `GET /health` — DB, Redis 연결 상태 확인 |

상세 내용: [V/40_observability.md](../V/40_observability.md)
