# V/40 — 관찰성 (Observability)

> 프로덕션 시스템 모니터링 전략 및 설정 가이드

---

## 1. 로깅 전략 (Logging)

### 로그 레벨 기준

| 레벨 | 사용 상황 | 예시 |
|------|---------|------|
| `DEBUG` | 개발 디버깅용 (Production에서 비활성화) | SQL 쿼리, 함수 진입 |
| `INFO` | 정상 이벤트 기록 | 사용자 로그인, 게시글 생성 |
| `WARNING` | 예상 가능한 이상 상황 | Rate Limit 접근, 비활성 FCM 토큰 |
| `ERROR` | 처리 실패 (복구 가능) | 외부 API 오류, DB 쿼리 실패 |
| `CRITICAL` | 시스템 중단 수준 | DB 연결 불가, Redis 연결 불가 |

### JSON 구조화 로그 설정

```python
# app/core/logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        # Request ID가 있으면 포함
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        # 에러이면 스택 트레이스 포함
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)

# 로거 초기화
def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO if settings.PRODUCTION else logging.DEBUG)
```

### 로그 패턴 예시

```python
import logging
logger = logging.getLogger(__name__)

class AuthService:
    async def login_google(self, id_token: str):
        try:
            user_info = await verify_google_token(id_token)
            logger.info("User logged in", extra={
                "event": "auth.login",
                "provider": "google",
                "user_id": user.id,
                # ❌ 절대 토큰을 로그에 포함하지 않음
            })
            return user
        except Exception as e:
            logger.error("Google login failed", extra={
                "event": "auth.login_failed",
                "provider": "google",
                "error": str(e)
                # ❌ id_token, access_token은 절대 포함하지 않음
            })
            raise
```

### 민감정보 로그 금지 목록

- `access_token`, `id_token`, `refresh_token`
- `DATABASE_URL` (비밀번호 포함)
- `JWT_SECRET_KEY`
- `FIREBASE_CREDENTIALS_JSON`
- `KAKAO_REST_API_KEY`, `NAVER_CLIENT_SECRET`
- FCM 토큰 (개인정보)
- 사용자 이메일 (INFO 이하 레벨에서)

---

## 2. 요청 추적 (Request Tracing)

### Request ID 미들웨어

```python
# middleware/request_id.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### 로그에 Request ID 포함

```python
# 모든 요청 로그에 request_id 포함
logger.info("Creating post", extra={
    "event": "board.post.create",
    "request_id": request.state.request_id,
    "user_id": current_user.id,
})
```

---

## 3. 모니터링 지표 (Metrics)

### 핵심 비즈니스 지표

| 지표 | 측정 방법 | 알림 조건 |
|------|---------|---------|
| 활성 사용자 수 | `users` 테이블 last_login | — |
| 일간 로그인 수 | auth.login 이벤트 카운트 | 전일 대비 50% 이상 감소 |
| 게시글 작성 수 | board.post.created 이벤트 | — |
| FCM 발송 성공률 | fcm.send.success / fcm.send.total | 성공률 < 90% |
| 읽지 않은 알림 평균 | push_notifications 평균 | > 50개/사용자 |

### 기술 지표

| 지표 | 측정 방법 | 알림 조건 |
|------|---------|---------|
| API 응답시간 (p95) | 요청 처리 시간 | > 500ms |
| API 응답시간 (p99) | 요청 처리 시간 | > 1,000ms |
| 에러율 | 5xx 응답 수 / 전체 요청 | > 1% |
| DB 쿼리 시간 | SQLAlchemy 이벤트 | 평균 > 50ms |
| Redis 캐시 히트율 | Cache hit / Cache total | < 70% |
| WebSocket 연결 수 | 활성 연결 게이지 | > 1,000 (경고) |
| DB 커넥션 풀 사용률 | pool_size 대비 사용 중 | > 80% |

### Prometheus 메트릭 설정 (선택)

```python
# 선택적 구현 — Prometheus + Grafana 연동 시
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
# /metrics 엔드포인트에서 메트릭 수집
```

---

## 4. 헬스체크 (Health Check)

### GET /health 구현

```python
# api/v1/endpoints/health.py
from fastapi import APIRouter
from app.core.database import get_db
from app.core.cache import get_cache

router = APIRouter()

@router.get("/health")
async def health_check():
    status = {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

    # DB 연결 확인
    try:
        async with get_db() as db:
            await db.execute(text("SELECT 1"))
        status["database"] = "connected"
    except Exception as e:
        status["database"] = "error"
        status["status"] = "unhealthy"
        logger.error("Database health check failed", extra={"error": str(e)})

    # Redis 연결 확인
    try:
        redis = await get_cache()
        await redis.ping()
        status["redis"] = "connected"
    except Exception as e:
        status["redis"] = "error"
        status["status"] = "degraded"
        logger.warning("Redis health check failed", extra={"error": str(e)})

    status_code = 200 if status["status"] == "healthy" else 503
    return JSONResponse(content=status, status_code=status_code)
```

### 헬스체크 응답 형식

```json
// 정상
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2026-03-03T12:00:00Z"
}

// 부분 장애 (Redis 문제)
{
  "status": "degraded",
  "database": "connected",
  "redis": "error",
  "timestamp": "2026-03-03T12:00:00Z"
}

// 전체 장애
{
  "status": "unhealthy",
  "database": "error",
  "redis": "connected",
  "timestamp": "2026-03-03T12:00:00Z"
}
```

### Cloud Run 헬스체크 설정

```yaml
# cloud-run-service.yaml
spec:
  template:
    spec:
      containers:
        - livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 30
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
```

---

## 5. 알림 규칙 (Alerting)

### 긴급 알림 (PagerDuty / Slack #alert-critical)

| 조건 | 임계값 | 지속 시간 |
|------|--------|---------|
| 헬스체크 실패 | 연속 3회 | 즉시 |
| API 에러율 | > 5% | 5분 |
| DB 연결 실패 | 1회 이상 | 즉시 |
| p99 응답시간 | > 3초 | 5분 |

### 경고 알림 (Slack #alert-warning)

| 조건 | 임계값 | 지속 시간 |
|------|--------|---------|
| p95 응답시간 | > 500ms | 10분 |
| DB 커넥션 풀 | > 80% 사용 | 5분 |
| FCM 발송 실패율 | > 10% | 10분 |
| Redis 캐시 히트율 | < 60% | 15분 |

---

## 6. GCP 모니터링 설정

```bash
# Cloud Monitoring 알림 정책 생성 (예시)
gcloud monitoring alert-policies create \
  --display-name="High API Latency" \
  --condition-display-name="p95 > 500ms" \
  --condition-filter="resource.type=cloud_run_revision AND metric.type=run.googleapis.com/request_latencies" \
  --condition-threshold-value=500 \
  --condition-threshold-comparison=COMPARISON_GT \
  --notification-channels=$SLACK_CHANNEL_ID
```

### Cloud Logging 쿼리

```sql
-- 에러 로그 조회
resource.type="cloud_run_revision"
severity>=ERROR
timestamp >= "2026-03-03T00:00:00Z"

-- 느린 요청 조회 (1초 이상)
resource.type="cloud_run_revision"
httpRequest.latency > "1s"

-- 특정 사용자 활동 추적
jsonPayload.user_id="123"
```

---

## 7. 로컬 개발 관찰성

```bash
# 구조화 로그 보기 좋게 출력
uvicorn app.main:app --reload | python -m json.tool

# 실시간 에러만 필터링
uvicorn app.main:app --reload 2>&1 | grep -E '"level":"(ERROR|CRITICAL)"'
```
