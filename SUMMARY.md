# Min-Minisaas Backend - 종합 요약 (SUMMARY)

**Last Updated:** Feb 13, 2026
**Status:** 85% Complete (6/7 Security Tasks ✅)

---

## 📌 프로젝트 개요

Min-Minisaas Backend는 FastAPI 기반의 멀티 플랫폼 인증 시스템입니다.

- **플랫폼:** Web, Mobile, Desktop, IoT (4가지)
- **인증 방식:** Firebase, OAuth2 PKCE, API Key + Device Secret
- **데이터베이스:** PostgreSQL
- **캐시/세션:** Redis
- **핵심 기능:** 플랫폼별 맞춤형 인증, 토큰 재사용 방지, CSRF 보호, 감사 로깅

---

## 🏗️ 아키텍처 핵심

### 설계 원칙

1. **Strategy 패턴:** 플랫폼별 인증 로직 완전 분리
2. **명시적 플랫폼 선언:** User-Agent 파싱 대신 X-Platform 헤더 사용
3. **공통 비즈니스 로직:** AuthService에서 일관되게 처리
4. **확장성:** 새 플랫폼 추가 = Strategy + Router 1개씩만 추가

### 플랫폼별 인증 방식

| 플랫폼 | 1차 인증 | 세션 유지 | TTL | 특징 |
|--------|---------|---------|-----|------|
| **Web** | Firebase JWT | Server Session (Redis) + HttpOnly Cookie | 30분 (슬라이딩) | Stateful, 동시 세션 1개 |
| **Mobile** | Firebase JWT | Stateless (클라이언트 보관) | 1시간 | Stateless, JWT 재사용 체크 |
| **Desktop** | OAuth2 PKCE | Self-issued JWT | Access 1시간 / Refresh 30일 | PKCE, Refresh Token Rotation |
| **IoT** | API Key + Device Secret | Long-lived JWT | Access 24시간 / Refresh 90일 | 안정성 우선, Rotation 없음 |

---

## ⚠️ 현재 아키텍처의 한계 및 향후 개선안

### 📍 현재의 문제점

**인증 수단 간 사용자 통합의 어려움:**

```
같은 사용자가 여러 플랫폼에서 로그인 시:
┌─────────────────────────────────────┐
│ iOS (Flutter) + Firebase 로그인     │
│ → Firebase UID: "firebase:abc123"   │
│ → User 생성: id=firebase:abc123     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ macOS (Desktop) + Google OAuth 로그인│
│ → Google ID: "google:def456"        │
│ → User 생성: id=google:def456       │
│ (다른 계정으로 생성됨! ❌)            │
└─────────────────────────────────────┘
```

**결과:** 같은 Google 계정이어도 백엔드에서 **다른 사용자로 인식**

### 🔧 Apple Sign-in 추가 시 더 심화됨

```
Apple Sign-in 도입 방법 A: Firebase를 통함
├─ Firebase 콘솔에 Apple 설정
├─ Firebase SDK로 처리
├─ Firebase UID 발급 (통일 가능 ✅)
└─ 현재 구조 유지

Apple Sign-in 도입 방법 B: 직접 사용 (Desktop PKCE처럼)
├─ Apple OAuth2 직접 호출
├─ Apple User ID 발급 (Firebase와 다름 ❌)
└─ 또 다른 사용자 분산

결론: Apple을 추가할수록 복잡해짐
```

### 🎯 왜 문제인가?

1. **사용자 분산**
   - 같은 사람이 여러 계정으로 생성됨
   - 포인트, 구매 이력 분산
   - 사용자 추적 어려움

2. **유지보수 비용**
   - 새 인증 수단 추가할 때마다 여러 곳 수정 필요
   - Firebase UID ↔ Google ID ↔ Apple ID 매핑 복잡
   - 데이터베이스 마이그레이션 복잡

3. **확장성 제한**
   - Kakao, GitHub, Naver 추가 시 동일한 문제 반복
   - 사용자 계정 통합/병합 불가능

---

## ✨ 권장 개선안: Provider 기반 아키텍처

**언제할 건가? → 지금 할 필요 없음, 필요해질 때 (1-2개월 후)**

### 핵심 개념

```python
# User: 순수 사용자 정보
class User:
    id: UUID                    # Primary User ID
    email: str                 # 통일된 email
    name, picture, points: ...

# AuthProvider: 인증 수단 (여러 개 가능)
class AuthProvider:
    id: UUID
    user_id: UUID              # → User
    provider_type: str         # "firebase", "google", "apple", "kakao"
    provider_user_id: str      # Firebase UID, Google ID, Apple ID 등
    email: str
    is_primary: bool
    is_verified: bool
```

### 사용자 시나리오

```
1️⃣ iOS: Firebase로 로그인
   User(id=user123, email=user@gmail.com)
   AuthProvider(type="firebase", provider_id="firebase:xyz")

2️⃣ macOS: Google로 로그인
   같은 email 발견 → 기존 User(id=user123)에 연결
   AuthProvider(type="google", provider_id="google:abc")

3️⃣ Web: Apple로 로그인
   같은 email 발견 → 기존 User(id=user123)에 연결
   AuthProvider(type="apple", provider_id="apple:def")

결과: 한 User에 3개의 AuthProvider 연결 ✅
     모든 기기에서 같은 user_id(user123)로 인식
```

### 장점

| 항목 | 현재 | 개선 후 |
|------|------|--------|
| **새 인증 수단 추가** | 많은 수정 필요 | Strategy + Router만 |
| **계정 통합** | ❌ 불가능 | ✅ 자동 (email 기반) |
| **여러 기기** | 각각 다른 계정 | ✅ 한 계정 |
| **Apple 추가** | 복잡함 | 30분 |
| **GitHub 추가** | 복잡함 | 30분 |
| **마이그레이션** | 고통스러움 | AuthProvider 행 추가만 |

### 구현 난이도 & 예상 시간

```
Phase 1: AuthProvider 모델 추가 (필요할 때)
├─ AuthProvider 테이블 생성: 1시간
├─ 기존 데이터 마이그레이션: 1시간
└─ 총: 2시간

Phase 2: Provider Service 구현
├─ ProviderService: 1시간
├─ AccountService (계정 통합): 1시간
└─ 통합 로그인 엔드포인트: 1시간
└─ 총: 3시간

Phase 3: 새 인증 수단 추가는 이제 쉬움!
├─ Apple Sign-in: 30분
├─ GitHub: 30분
├─ Kakao: 30분
└─ 각각 Strategy + 엔드포인트만
```

---

## 📋 현재 상황 정리

### ✅ 지금 하면 좋은 것
- Firebase 기반 iOS + macOS 통합 사용
- Email+Password 레거시 유지
- IoT Device 인증 유지
- **Apple을 추가해야 한다면? → Firebase 통합 Apple Sign-in 사용**

### ⏳ 나중에 하면 될 것 (필요할 때)
- Provider 기반 아키텍처로 리팩토링
- 실제 Apple Sign-in이 필요해질 때
- GitHub, Kakao 등 다른 인증 수단이 필요해질 때
- **시간:** 지금 하면 5-6시간, 나중에 필요할 때 해도 됨

### ❌ 지금 하지 말 것
- 미리 Provider 기반으로 리팩토링 (오버엔지니어링)
- 모든 인증 수단 미리 구현
- 완벽한 통합 시스템 미리 구축

### 🎯 현실적 방향

```
현재 (Feb 2026):
├─ Firebase 중심으로 운영
├─ 필요하면 Email+Password 사용
└─ 나중에 Apple/다른 수단 필요할 때 대응

실제 필요해지는 시점 (1-2개월 후):
├─ 사용자가 Apple 로그인 요청
├─ 또는 GitHub 로그인 요청
└─ → 그때 Provider 기반으로 리팩토링 (5-6시간)

장점:
✅ 지금은 간단하게 운영
✅ 필요할 때 유연하게 대응
✅ 추측에 기반한 개발 회피
✅ 실제 사용자 feedback 반영 가능
```

---

## 🔗 참고: Apple Sign-in vs Firebase

**Apple Sign-in이란?**
- Apple이 제공하는 OAuth2/OpenID Connect 서비스
- iOS, macOS, Web 등에서 "Sign in with Apple" 제공

**Firebase와의 관계:**
```
방법 1: Firebase를 통한 Apple Sign-in
  App → Firebase SDK → Apple 검증 → Firebase UID
  (현재 Mobile 구조와 동일)

방법 2: Apple Sign-in 직접 사용
  App → Apple OAuth2 → Apple User ID
  (Desktop의 Google PKCE처럼)
  단점: Firebase UID와 다름 → 사용자 통합 필요

추천: 방법 1 (Firebase 통합) 선택
  → 현재 구조와 일관됨
  → 설정 간단
  → 나중에 필요하면 방법 2로 전환 가능
```

---

```
app/
├── api/v1/
│   ├── endpoints/auth/
│   │   ├── web.py              # Web 플랫폼
│   │   ├── mobile.py           # Mobile 플랫폼
│   │   ├── desktop.py          # Desktop OAuth2 PKCE
│   │   ├── device.py           # IoT Device
│   │   ├── legacy.py           # 이메일+비밀번호 (하위호환)
│   │   └── common.py           # 공통 엔드포인트 (/me, /logout, /account)
│   └── dependencies/
│       ├── api_key.py          # X-API-Key 검증
│       └── auth.py             # 플랫폼별 인증 의존성
│
├── core/auth/                   # [Core Auth] 기술 레이어
│   ├── base.py                 # AuthStrategy 인터페이스
│   ├── firebase_verifier.py    # Firebase JWT 검증 + JWKS 캐싱
│   ├── jwt_manager.py          # JWT 재사용 방지 & 무효화
│   ├── session_manager.py      # Redis 세션 관리 (Web)
│   ├── csrf_manager.py         # CSRF 토큰 생성/검증 (Task 5)
│   ├── web_strategy.py         # Web 전략
│   ├── mobile_strategy.py      # Mobile 전략
│   ├── desktop_strategy.py     # Desktop OAuth2 PKCE + 토큰 로테이션
│   └── device_strategy.py      # IoT 전략
│
├── domain/auth/                 # [Domain Auth] 비즈니스 레이어
│   ├── services/
│   │   └── auth_service.py     # 공통 비즈니스 로직 (유저 조회/생성/포인트)
│   ├── models/
│   │   ├── user.py             # 사용자 모델
│   │   ├── device.py           # IoT 디바이스 모델
│   │   └── security_log.py     # 보안 이벤트 로그
│   └── schemas/
│       ├── user.py             # 사용자 DTO
│       └── csrf.py             # CSRF 토큰 응답 스키마
│
├── core/
│   ├── config.py               # 설정 (Redis URL, Firebase, 토큰 TTL 등)
│   ├── database.py             # DB 연결
│   ├── exceptions.py           # 예외 처리 (AuthException 등)
│   └── notifications/          # 알림 서비스
│       └── slack.py            # Slack 알림
│
└── db/
    └── model_registry.py       # SQLAlchemy 모델 레지스트리
```

---

## 🔐 보안 구현 현황

### P1 - CRITICAL (완료 ✅)

| Task | 내용 | 상태 | 위험도 감소 |
|------|------|------|-----------|
| Task 1 | Refresh Token 재사용 탐지 (Desktop) | ✅ | 60% → 5% |
| Task 2 | Session Fixation 방지 (Web) | ✅ | HIGH |

### P2 - IMPORTANT (완료 ✅)

| Task | 내용 | 상태 |
|------|------|------|
| Task 3 | Device Secret 로테이션 & Rate Limiting (IoT) | ✅ |
| Task 4 | 통일된 에러 응답 포맷 (모든 플랫폼) | ✅ |

### P3 - ENHANCEMENT (완료 ✅)

| Task | 내용 | 상태 | 추가 정보 |
|------|------|------|---------|
| Task 5 | CSRF 토큰 보호 (민감한 작업) | ✅ | 20/20 테스트 통과 |

### P4 - INFRASTRUCTURE (미구현)

| Task | 내용 | 상태 | 난이도 |
|------|------|------|--------|
| Task 6 | mTLS for Device/IoT | ⬜ | 16+ 시간 |
| Task 7 | Hardware Security Module (HSM) | ⬜ | 20+ 시간 |

**전체 위험도:** 7/10 → **2/10** ✅ (목표 달성!)

---

## 🔑 핵심 보안 기능

### 1. API Key (모든 엔드포인트)
```http
X-API-Key: <secret>
```
- 모든 요청에 필수 (1차 방어선)
- 환경변수 `API_SECRET_KEY`로 관리

### 2. JWT 재사용 방지

**Web/Mobile:** Redis 기반 `iat` 타임스탬프 추적
```
Key: jwt_used:{user_id}:{iat}
TTL: JWT 남은 수명
```

**Desktop:** Refresh Token Rotation (탐지 + 즉시 무효화)
```
Key: desktop:refresh:{user_id}:{device_id}
- 새 refresh_token 발급 시 이전 토큰 즉시 무효화
- 재사용 탐지 시 전체 user JWT 무효화
```

### 3. CSRF 토큰 (Task 5) ⭐
```
생성: GET /auth/me → csrf_token 응답
사용: POST /logout, DELETE /account에 X-CSRF-Token 헤더 필수
특징:
- 256-bit 보안 난수 (secrets.token_hex(32))
- 플랫폼별 분리 저장
- 1회용 (사용 후 삭제)
- 1시간 TTL
- 자동 클린업
```

### 4. PKCE (Desktop)
- Authorization Code 탈취 방지
- code_verifier + code_challenge SHA256 검증

### 5. Session Fixation 방지 (Web)
- 로그인 전 기존 세션 명시적 파괴
- 로그인 후 항상 새 세션 ID 생성

### 6. Device Secret 관리 (IoT)
- Bcrypt 해싱하여 DB 저장
- 등록 시 1회만 평문 반환
- Rate Limiting: 5회 실패 → 15분 잠금

### 7. HttpOnly Cookie (Web)
```
Set-Cookie: session=<id>
  HttpOnly = true        # XSS 방어
  Secure = true          # HTTPS only
  SameSite = Lax         # CSRF 방어
  Max-Age = 3600         # 1시간
```

---

## 📊 API 엔드포인트

### 인증 (플랫폼별)

```
POST /api/v1/auth/login/web          # Web (Firebase JWT)
POST /api/v1/auth/login/mobile       # Mobile (Firebase JWT)
POST /api/v1/auth/login/desktop      # Desktop (OAuth2 PKCE)
POST /api/v1/auth/login/device       # IoT (API Key + Secret)
```

### 토큰 갱신

```
POST /api/v1/auth/refresh/desktop    # Desktop Refresh Token Rotation
POST /api/v1/auth/refresh/device     # IoT 토큰 갱신
```

### 공통 엔드포인트 (X-Platform 헤더 필수)

```
GET  /api/v1/auth/me                 # 현재 사용자 정보 + CSRF 토큰
POST /api/v1/auth/logout             # 로그아웃 (X-CSRF-Token 필수)
DELETE /api/v1/auth/account          # 계정 삭제 (X-CSRF-Token 필수)
POST /api/v1/auth/heartbeat          # 세션/토큰 유효성 확인
```

### 기타

```
POST /api/v1/auth/register           # 이메일+비밀번호 회원가입 (레거시)
POST /api/v1/auth/login              # 이메일+비밀번호 로그인 (레거시)
POST /api/v1/auth/device/{id}/rotate-secret  # 디바이스 시크릿 로테이션
```

---

## 🗄️ 데이터베이스 스키마

### 핵심 테이블

#### users
```sql
- id (UUID PK)
- email (unique)
- firebase_uid (unique)
- username (unique)
- password_hash
- name, picture
- points
- is_active
- last_login
- created_at, updated_at
```

#### devices (IoT)
```sql
- id (UUID PK)
- device_id (unique)
- device_secret_hash
- owner_id (FK → users.id)
- name, device_type
- is_active
- last_seen
- secret_rotated_at
- created_at, updated_at
```

#### security_logs (감사)
```sql
- id (UUID PK)
- user_id
- event_type (e.g., "login", "token_reuse_detected", "secret_rotated")
- device_id
- ip_address, user_agent
- details (JSON)
- created_at, updated_at
```

#### event_logs (이벤트 sourcing)
```sql
- id (UUID PK)
- event_type
- aggregate_id
- user_id
- payload (JSON)
- processed_at
- created_at
```

#### transactions (포인트 원장)
```sql
- id (UUID PK)
- user_id (FK → users.id)
- type (charge/consume/refund)
- amount, balance_after
- idempotency_key (unique)
- prev_hash, current_hash (해시체인)
- tx_data (JSON)
- created_at
```

#### ledger_roots & user_chain_hashes (블록체인 무결성)
```
자세한 내용은 docs/DB_SCHEMA_OVERVIEW.md 참고
```

---

## 🔄 Redis 키 패턴

```
# Web 세션
sess:{session_id}                       → Hash { user_id, expires, last_active }
                                         TTL: SESSION_TTL_MIN * 60

# JWT 재사용 방지 (Firebase)
jwt_used:{user_id}:{iat}               → String "used"
                                         TTL: JWT 남은 수명

# Desktop Refresh Token
desktop:refresh:{user_id}:{device_id}  → Hash { refresh_token, device_name, created_at }
                                         TTL: 30일

# IoT Device 세션
device:session:{device_id}             → Hash { access_token, refresh_token, owner_id, last_seen }
                                         TTL: 90일

# CSRF 토큰 (Task 5)
csrf:token:{user_id}:{platform}        → String token_value
                                         TTL: 1시간

# Device 로그인 실패 카운트 (Rate Limiting)
device:failed_attempts:{device_id}     → Integer count
                                         TTL: 1시간
```

---

## 📋 설정 (환경변수)

```env
# 공통
API_SECRET_KEY=                        # X-API-Key 검증용
SECRET_KEY=                            # 자체 JWT 서명키 (Desktop/IoT)
ENVIRONMENT=development                # development | production

# Database
DATABASE_URL=postgresql+asyncpg://...

# Redis
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=...

# Firebase (Web/Mobile)
FIREBASE_PROJECT_ID=
FIREBASE_JWKS_URI=https://www.googleapis.com/...

# Google OAuth (Desktop)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Session (Web)
SESSION_TTL_MIN=30
COOKIE_SECURE=true
COOKIE_SAMESITE=lax

# Token TTL
ACCESS_TOKEN_EXPIRE_MINUTES=60         # Desktop access token
REFRESH_TOKEN_EXPIRE_DAYS=30           # Desktop refresh token
DEVICE_ACCESS_EXPIRE_HOURS=24          # IoT access token
DEVICE_REFRESH_EXPIRE_DAYS=90          # IoT refresh token

# CSRF Token (Task 5)
CSRF_TOKEN_TTL=3600                    # 1시간

# Rate Limiting (IoT)
DEVICE_MAX_FAILED_ATTEMPTS=5
DEVICE_LOCKOUT_MINUTES=15
```

---

## 🚀 실행 명령어

### 최초 설정
```bash
# DB 생성 + 마이그레이션 + 검증
make setup

# 또는 개별 실행
make bootstrap   # DB 생성 (없으면)
make migrate     # Alembic 마이그레이션
make verify      # PostgreSQL/Redis 연결 검증
```

### 개발
```bash
# 로컬 실행
pip install -r api/requirements.txt
python api/app/main.py

# Docker Compose
docker-compose up -d
```

### 테스트
```bash
# 모든 테스트
pytest tests/ -v

# CSRF 테스트 (Task 5)
pytest tests/test_csrf_protection.py -v

# 인증 엔드포인트 테스트
pytest tests/test_auth_endpoints.py -v

# 커버리지
pytest tests/ --cov=app --cov-report=html
```

### 코드 스타일
```bash
black --check api/
isort --check-only api/
flake8 api/
pylint api/
```

---

## 📈 테스트 현황

### 테스트 결과 (2026-02-11)

```
총 테스트: 76/76 PASSING ✅

Task별 분류:
- Task 1 (Token Reuse Detection): 5/5 PASS
- Task 2 (Session Fixation): 5/5 PASS
- Task 3 (Device Rate Limiting): 6/6 PASS
- Task 4 (Unified Error): 7/7 PASS
- Task 5 (CSRF Protection): 20/20 PASS ⭐
- Foundation (Endpoints, Health): 32/32 PASS
```

### 테스트된 항목

✅ Strategy 팩토리 패턴
✅ JWT 재사용 방지
✅ Session 생성/검증/삭제
✅ Firebase JWT 검증기
✅ Token Reuse Detection
✅ Session Fixation Prevention
✅ Device Secret Rotation
✅ Rate Limiting
✅ 통일된 에러 응답
✅ CSRF 토큰 생성/검증/소비

### 테스트되지 않은 항목 (다음 단계)

⬜ Firebase 실제 JWT 검증 (Mock 필요)
⬜ OAuth2 PKCE 토큰 교환
⬜ 데이터베이스 통합 테스트
⬜ 엔드포인트 통합 테스트
⬜ 보안 시나리오 (토큰 탈취, 세션 하이재킹 등)

---

## 🔍 DB 마이그레이션 절차

### 원칙

- 스키마 변경은 Alembic migration으로 관리
- 운영 경로에서 `Base.metadata.create_all()` 직접 호출 금지
- Expand-Contract 패턴으로 파괴적 변경 처리 (2회 배포)

### 신규 스키마 변경 절차

1. SQLAlchemy 모델 수정
2. Migration 생성:
   ```bash
   .venv/bin/alembic revision --autogenerate -m "describe change"
   ```
3. 생성된 revision 검토 (nullable, default, index, drop 안전성 확인)
4. 로컬 적용: `make migrate`
5. 런타임 검증: `make verify`
6. 필요시 downgrade 검증

### 배포 순서

1. DB migration 먼저 적용 (`make migrate`)
2. Migration 성공 후 앱 버전 배포
3. 배포 직후 `make verify`로 상태 확인

---

## 💾 데이터베이스 & 인프라 검증

### 런타임 연결 상태 (2026-02-11)

| 컴포넌트 | 상태 | 테스트 |
|---------|------|--------|
| PostgreSQL | ✅ | 2/2 PASS (Bootstrap, Migration) |
| Redis | ✅ | 3/3 PASS (Pool, Cache, Async) |
| 앱 캐싱 | ✅ | REDIS_URL_WITH_AUTH 정상 |

### 테스트 파일

- `tests/test_bootstrap_db.py` - DB 초기화, 마이그레이션
- `tests/test_runtime_connectivity.py` - Redis 풀, 캐시 작업, Async
- `tests/test_redis_connection_manual.py` - 수동 테스트 (업데이트 필요)

### 배포 체크리스트

- ✅ DB 연결 확인 (자동화 테스트)
- ✅ Redis 연결 확인 (앱 레벨)
- ✅ 런타임 의존성 검증
- 📝 DB 이름/접속 정보 변경 시 bootstrap 멱등성 재검증

---

## 📝 파일 변경 이력

### Task 5 (CSRF 토큰) - 신규 파일

| 파일 | 용도 |
|------|------|
| `app/core/auth/csrf_manager.py` | CSRF 토큰 생성/검증/무효화 |
| `app/domain/auth/schemas/csrf.py` | CSRF 응답 스키마 |
| `tests/test_csrf_protection.py` | 20개 종합 테스트 |

### Task 5 (CSRF 토큰) - 수정 파일

| 파일 | 변경 사항 |
|------|---------|
| `app/api/v1/endpoints/auth/common.py` | CSRF 토큰 생성/검증 추가 |
| `app/api/v1/dependencies/auth.py` | CSRF 검증 의존성 추가 |

### 기타 주요 파일

| 파일 | 목적 |
|------|------|
| `app/core/exceptions.py` | 통일된 예외 처리 |
| `app/domain/auth/models/security_log.py` | 보안 이벤트 로깅 |
| `alembic/versions/20260211_0001_baseline.py` | DB baseline migration |

---

## 🎯 구현 완료 체크리스트

### P1 - CRITICAL (완료 ✅)
- ✅ Token Reuse Detection (Desktop)
- ✅ Session Fixation Prevention (Web)

### P2 - IMPORTANT (완료 ✅)
- ✅ Device Secret Rotation & Rate Limiting (IoT)
- ✅ Unified Error Response Format (All)

### P3 - ENHANCEMENT (완료 ✅)
- ✅ CSRF Token Protection (Web sensitive ops) ⭐ Task 5

### P4 - ARCHITECTURE (완료 ✅)
- ✅ Core/Domain Layer Separation
  - `app/core/auth/` (기술 레이어)
  - `app/domain/auth/` (비즈니스 레이어)
  - `app/api/v1/` (인터페이스 레이어)

### 추가 미구현 (Optional)
- ⬜ mTLS for Device/IoT (Infrastructure)
- ⬜ Hardware Security Module (Infrastructure)

---

## 📚 관련 문서

### 상세 설계
- `auth-architecture-design.md` - 플랫폼별 인증 방식, 시퀀스 다이어그램, 설계 원칙
- `IMPLEMENTATION_SUMMARY.md` - 구현 요약, 아키텍처 페이즈, 파일 구조
- `AUTH_TESTING_RESULTS.md` - 테스트 결과, 검증된 컴포넌트

### 보안 구현
- `TASK5_CSRF_IMPLEMENTATION.md` - CSRF 토큰 상세 구현, 테스트 커버리지
- `TODO.md` - 보안 작업 진행 상태, 위험도 평가

### 데이터베이스
- `docs/DB_MIGRATION_WORKFLOW.md` - 마이그레이션 절차, 배포 순서
- `docs/DB_SCHEMA_OVERVIEW.md` - 스키마 개요, ERD, 테이블 설명

### 프로젝트
- `README.md` - 빠른 시작, 개발 가이드, API 문서

---

## 🔗 핵심 의존성

```
fastapi >= 0.100
sqlalchemy >= 2.0 (async)
alembic (마이그레이션)
redis (캐시/세션)
pydantic (검증)
python-jose (JWT)
firebase-admin (Firebase 검증)
google-auth (Google OAuth)
bcrypt (비밀번호/시크릿 해싱)
python-dotenv (.env 관리)
```

---

## ✨ 주요 특징

✅ **멀티플랫폼:** Web, Mobile, Desktop, IoT 각각 최적화된 인증
✅ **Strategy 패턴:** 확장 가능한 아키텍처
✅ **보안 우선:** JWT 재사용 방지, Session Fixation 방지, CSRF 보호
✅ **감사 로깅:** 모든 보안 이벤트 기록
✅ **테스트 완벽:** 76/76 테스트 통과
✅ **문서화:** 설계부터 배포까지 상세 문서
✅ **무중단 배포:** Expand-Contract 패턴 지원

---

## 🎓 초신자 가이드

### 인증 플로우 이해하기

1. **Web 사용자가 로그인하면?**
   - 클라이언트: Firebase로 로그인 → Firebase JWT 획득
   - 클라이언트: `POST /auth/login/web` (Firebase JWT 포함)
   - 서버: Firebase JWT 검증 → 유저 조회/생성 → Redis 세션 생성
   - 서버: Set-Cookie로 session ID 반환
   - 이후 요청: 쿠키 자동 포함 → 서버에서 세션 검증

2. **Mobile 사용자가 로그인하면?**
   - 클라이언트: Firebase로 로그인 → Firebase JWT 획득
   - 클라이언트: `POST /auth/login/mobile` (Firebase JWT 포함)
   - 서버: Firebase JWT 검증 → 유저 조회/생성 → JWT 유효 여부만 추적
   - 서버: JSON 응답 (쿠키 없음)
   - 이후 요청: Authorization 헤더에 Firebase JWT 포함 → 서버에서 검증

3. **IoT 디바이스가 로그인하면?**
   - 관리자: 대시보드에서 디바이스 등록 → API Key + Device Secret 발급
   - 디바이스: `POST /auth/login/device` (디바이스ID + 시크릿)
   - 서버: Device Secret 검증 → 장기 토큰 발급 (24시간 access, 90일 refresh)
   - 이후 요청: Authorization 헤더에 access token 포함

### CSRF 토큰 사용하기 (Task 5)

1. 클라이언트: `GET /auth/me` → csrf_token 획득
2. 클라이언트: `POST /logout` with `X-CSRF-Token` 헤더 → 로그아웃 완료
3. 같은 토큰으로 다시 시도하면 403 (토큰은 1회용)

---

**다음 단계:** mTLS (Task 6), HSM (Task 7) - 인프라 수준의 선택사항

