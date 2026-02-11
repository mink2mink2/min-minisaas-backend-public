# Multi-Platform Auth Architecture Design

> 기존 pdf-helper-bapi의 인증 시스템을 분석하고, 강결합 문제를 해결하여
> Web / Mobile / Desktop / IoT를 지원하는 확장 가능한 인증 아키텍처 설계

---

## 1. 현재 상태 분석

### 1.1 pdf-helper-bapi (실서비스) - 문제점

```
auth_router.py login() 함수 하나에 모든 로직이 집중:
├─ Firebase JWT 검증
├─ User-Agent 파싱으로 플랫폼 판별 (fragile)
├─ 유저 조회/생성/포인트 지급
├─ if is_browser → 세션 생성 + 쿠키 Set
├─ if is_mobile_app → JWT stateless 반환
└─ 신규/기존/복구 유저 분기 × 플랫폼 분기 = 조건문 지옥
```

**핵심 문제:**
- 플랫폼 판별이 User-Agent 파싱에 의존 (Desktop 앱이 Chrome User-Agent를 쓰면?)
- 하나의 login() 함수가 200줄 (비즈니스 로직 + 플랫폼 로직 + 세션 로직 혼재)
- 새 플랫폼(Desktop, IoT) 추가 시 기존 코드에 조건문 계속 추가 필요
- `verify_auth`와 `verify_auth_flexible`이 병존 (리팩토링 미완성)

### 1.2 min-minisaas-backend (현재) - 상태

- email+password → 자체 JWT 발급하는 기본 구조만 존재
- 세션 관리, 소셜 로그인, 플랫폼 분리 없음
- 대부분의 엔드포인트가 placeholder

---

## 2. 설계 원칙

1. **인증 방식(Strategy)과 비즈니스 로직(Service)의 완전 분리**
2. **플랫폼 판별은 클라이언트가 명시적으로 선언** (User-Agent 파싱 금지)
3. **공통 로직은 1회만 작성**, 플랫폼별 차이만 Strategy에서 처리
4. **새 플랫폼 추가 = Strategy 1개 + Router 1개 추가** (기존 코드 수정 없음)

---

## 3. 플랫폼별 인증 방식 매트릭스

| | Web | Mobile | Desktop | IoT |
|---|---|---|---|---|
| **1차 인증** | Firebase JWT | Firebase JWT | OAuth2 PKCE | API Key + Device Cert |
| **세션 유지** | Server Session (Redis) + HttpOnly Cookie | Stateless (클라이언트 보관) | Refresh Token (로컬 암호화 저장) | Long-lived Token |
| **세션 만료** | Sliding Window (30분, 활동 시 연장) | Firebase JWT exp (1시간) | Access 1시간 / Refresh 30일 | Access 24시간 / Refresh 90일 |
| **Heartbeat** | `/heartbeat` (세션 슬라이딩) | `/jwt-heartbeat` (만료 확인) | `/token-heartbeat` (만료 확인) | 없음 (긴 TTL) |
| **로그아웃** | 서버 세션 파괴 + 쿠키 삭제 + JWT 무효화 | 클라이언트 토큰 삭제 | Refresh Token 무효화 | API Key 비활성화 |
| **동시 세션** | 1개 (새 로그인 시 기존 파괴) | 기기당 1개 | 기기당 1개 | 무제한 |
| **API Key 필수** | O | O | O | O (자체가 인증 수단) |
| **토큰 재사용 방지** | 세션으로 관리 | JWT 1회용 체크 (Redis) | Refresh Rotation | N/A |

---

## 4. 디렉토리 구조

```
app/
├── api/v1/
│   ├── endpoints/
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── web.py              # POST /auth/login/web
│   │   │   ├── mobile.py           # POST /auth/login/mobile
│   │   │   ├── desktop.py          # POST /auth/login/desktop
│   │   │   ├── device.py           # POST /auth/login/device (IoT)
│   │   │   └── common.py           # POST /auth/logout, /auth/me, /auth/heartbeat
│   │   └── ...
│   └── dependencies/
│       ├── __init__.py
│       ├── api_key.py              # X-API-Key 검증 (공통)
│       └── auth.py                 # 플랫폼별 인증 의존성 (verify_web, verify_mobile, ...)
│
├── core/
│   ├── config.py
│   ├── database.py
│   ├── cache.py                    # Redis 래퍼
│   └── events.py                   # Event Bus
│
├── models/
│   ├── user.py                     # User 모델
│   ├── device.py                   # IoT Device 모델 (신규)
│   └── ...
│
├── schemas/
│   ├── auth.py                     # 인증 관련 Request/Response
│   └── user.py
│
├── services/
│   ├── auth_service.py             # 공통 비즈니스 로직 (유저 조회/생성/포인트)
│   └── ...
│
├── auth/                           # ★ 인증 전략 모듈 (신규)
│   ├── __init__.py
│   ├── base.py                     # AuthStrategy 추상 클래스
│   ├── web_strategy.py             # Web: Firebase → Session+Cookie
│   ├── mobile_strategy.py          # Mobile: Firebase → Stateless JWT
│   ├── desktop_strategy.py         # Desktop: OAuth2 PKCE → Refresh Token
│   ├── device_strategy.py          # IoT: API Key + Certificate
│   ├── firebase_verifier.py        # Firebase JWT 검증 (web/mobile 공유)
│   ├── jwt_manager.py              # JWT 재사용 방지 & 무효화
│   └── session_manager.py          # 서버사이드 세션 관리 (Redis)
│
└── middleware/
    ├── cors.py
    └── error_handler.py
```

---

## 5. 핵심 인터페이스 설계

### 5.1 AuthStrategy (추상 클래스)

```python
# app/auth/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from fastapi import Request
from fastapi.responses import Response


@dataclass
class AuthResult:
    """인증 결과 (모든 전략이 동일한 형태로 반환)"""
    user_id: str
    email: Optional[str]
    name: Optional[str]
    picture: Optional[str]
    platform: str                   # "web" | "mobile" | "desktop" | "device"
    auth_type: str                  # "firebase" | "oauth_pkce" | "api_key"
    expires: int                    # 세션/토큰 만료 Unix timestamp
    metadata: dict = None           # 플랫폼별 추가 데이터


@dataclass
class TokenPair:
    """토큰 쌍 (Desktop/IoT용 자체 토큰)"""
    access_token: str
    refresh_token: str
    access_expires: int
    refresh_expires: int


class AuthStrategy(ABC):
    """인증 전략 인터페이스"""

    @abstractmethod
    async def authenticate(self, request: Request, **kwargs) -> AuthResult:
        """
        인증 수행 - 클라이언트가 보낸 자격증명을 검증하고 AuthResult 반환

        Raises:
            HTTPException: 인증 실패 시
        """
        ...

    @abstractmethod
    async def create_session(self, auth_result: AuthResult) -> dict:
        """
        세션/토큰 생성 - 인증 성공 후 세션 또는 토큰을 생성

        Returns:
            세션 데이터 dict (전략별로 내용이 다름)
            - Web: {"session_id": "...", "expires": ...}
            - Mobile: {"expires": ...}  (JWT 자체가 세션)
            - Desktop: {"access_token": "...", "refresh_token": "...", ...}
            - IoT: {"access_token": "...", "refresh_token": "...", ...}
        """
        ...

    @abstractmethod
    async def build_response(
        self, response_data: dict, session_data: dict
    ) -> Response:
        """
        최종 HTTP 응답 생성 - 플랫폼별 응답 형태 (쿠키 포함 여부 등)

        - Web: JSONResponse + Set-Cookie (session)
        - Mobile/Desktop/IoT: JSONResponse only
        """
        ...

    @abstractmethod
    async def logout(self, request: Request, user_id: str) -> None:
        """로그아웃 처리 - 플랫폼별 세션/토큰 정리"""
        ...

    @abstractmethod
    async def heartbeat(self, request: Request) -> dict:
        """
        세션/토큰 유효성 확인

        Returns:
            {"valid": bool, "expires": int}
        """
        ...

    @abstractmethod
    async def refresh(self, request: Request) -> dict:
        """
        토큰 갱신 (해당되는 전략만)

        Returns:
            새 토큰 데이터 또는 갱신된 세션 정보
        """
        ...
```

### 5.2 전략 팩토리

```python
# app/auth/__init__.py
from app.auth.base import AuthStrategy
from app.auth.web_strategy import WebAuthStrategy
from app.auth.mobile_strategy import MobileAuthStrategy
from app.auth.desktop_strategy import DesktopAuthStrategy
from app.auth.device_strategy import DeviceAuthStrategy


_strategies: dict[str, AuthStrategy] = {
    "web": WebAuthStrategy(),
    "mobile": MobileAuthStrategy(),
    "desktop": DesktopAuthStrategy(),
    "device": DeviceAuthStrategy(),
}


def get_strategy(platform: str) -> AuthStrategy:
    strategy = _strategies.get(platform)
    if not strategy:
        raise ValueError(f"Unknown platform: {platform}")
    return strategy
```

---

## 6. 플랫폼별 전략 상세 설계

### 6.1 WebAuthStrategy

```
인증 흐름:
  Client → Firebase Login (Google 등) → Firebase JWT 획득
  Client → POST /auth/login/web (Authorization: Bearer <firebase_jwt>)
  Server → Firebase JWT 검증 → 유저 조회/생성 → Redis 세션 생성 → Set-Cookie 응답

후속 요청:
  Client → 요청 (Cookie: session=xxx 자동 포함)
  Server → 쿠키에서 session_id 추출 → Redis 세션 검증 → 슬라이딩 윈도우 갱신

로그아웃:
  Client → POST /auth/logout (Cookie 포함)
  Server → Redis 세션 삭제 → JWT 무효화 → 쿠키 삭제
```

```python
# app/auth/web_strategy.py
class WebAuthStrategy(AuthStrategy):
    """Web: Firebase JWT → Server Session + HttpOnly Cookie"""

    async def authenticate(self, request: Request, **kwargs) -> AuthResult:
        # 1. Authorization 헤더에서 Firebase JWT 추출
        # 2. firebase_verifier.verify() 호출
        # 3. JWT 재사용 체크 (jwt_manager.check_and_mark_used)
        # 4. AuthResult 반환
        ...

    async def create_session(self, auth_result: AuthResult) -> dict:
        # 1. 기존 세션 파괴 (동시 세션 1개 제한)
        #    session_manager.destroy_user_sessions(user_id)
        # 2. 새 세션 생성
        #    session_id = session_manager.create(user_id)
        # 3. 세션 정보 반환
        return {"session_id": session_id, "expires": expires_ts}

    async def build_response(self, response_data, session_data) -> Response:
        # JSONResponse + Set-Cookie (HttpOnly, Secure, SameSite=Lax)
        ...

    async def logout(self, request: Request, user_id: str) -> None:
        # 1. 쿠키에서 session_id 추출
        # 2. session_manager.destroy(session_id)
        # 3. jwt_manager.revoke_all_user_jwts(user_id)
        ...

    async def heartbeat(self, request: Request) -> dict:
        # 1. 쿠키에서 session_id 추출
        # 2. session_manager.validate_and_slide(session_id)
        # 3. 갱신된 만료 시각 반환
        ...

    async def refresh(self, request: Request) -> dict:
        # Web은 세션 기반이므로 heartbeat가 refresh 역할
        # heartbeat()로 위임
        ...
```

### 6.2 MobileAuthStrategy

```
인증 흐름:
  Client → Firebase Login → Firebase JWT 획득
  Client → POST /auth/login/mobile (Authorization: Bearer <firebase_jwt>)
  Server → Firebase JWT 검증 → 유저 조회/생성 → JSON 응답 (쿠키 없음)

후속 요청:
  Client → 요청 (Authorization: Bearer <firebase_jwt>)
  Server → Firebase JWT 검증 → JWT 재사용 체크

참고:
  - Firebase JWT는 1시간 만료, Firebase SDK가 자동 갱신
  - 서버는 Stateless (세션 저장 안 함)
  - JWT 재사용 방지만 Redis에서 관리
```

```python
# app/auth/mobile_strategy.py
class MobileAuthStrategy(AuthStrategy):
    """Mobile: Firebase JWT (Stateless)"""

    async def authenticate(self, request: Request, **kwargs) -> AuthResult:
        # 1. Authorization 헤더에서 Firebase JWT 추출
        # 2. firebase_verifier.verify() 호출
        # 3. JWT 재사용 체크
        # 4. AuthResult 반환 (expires = JWT exp)
        ...

    async def create_session(self, auth_result: AuthResult) -> dict:
        # Stateless - 세션 생성 안 함
        return {"expires": auth_result.expires}

    async def build_response(self, response_data, session_data) -> Response:
        # JSONResponse only (쿠키 없음)
        ...

    async def logout(self, request: Request, user_id: str) -> None:
        # Stateless - 서버에서 할 것 없음
        # 클라이언트가 토큰 삭제
        ...

    async def heartbeat(self, request: Request) -> dict:
        # Firebase JWT 검증만 수행
        # JWT exp 반환
        ...

    async def refresh(self, request: Request) -> dict:
        # Firebase SDK가 자동 갱신하므로 서버에서 처리 불필요
        raise NotImplementedError("Mobile uses Firebase SDK auto-refresh")
```

### 6.3 DesktopAuthStrategy

```
인증 흐름 (OAuth2 PKCE):
  Client → 로컬 HTTP 서버 시작 (예: localhost:9876)
  Client → 시스템 브라우저로 OAuth 페이지 오픈
           https://accounts.google.com/o/oauth2/v2/auth
           ?response_type=code
           &client_id=...
           &redirect_uri=http://localhost:9876/callback
           &code_challenge=<PKCE_CHALLENGE>
           &code_challenge_method=S256
           &scope=openid email profile
  User   → 브라우저에서 Google 로그인 & 동의
  Google → redirect_uri로 authorization_code 전달
  Client → authorization_code 수신
  Client → POST /auth/login/desktop
           Body: { "code": "<auth_code>", "code_verifier": "<pkce_verifier>" }
  Server → Google Token Exchange (code → id_token + access_token)
  Server → id_token 검증 → 유저 조회/생성
  Server → 자체 JWT 발급 (Access + Refresh)
  Server → JSON 응답

후속 요청:
  Client → Authorization: Bearer <access_token>
  Server → 자체 JWT 검증

토큰 갱신:
  Client → POST /auth/refresh/desktop
           Body: { "refresh_token": "<refresh_token>" }
  Server → Refresh Token Rotation → 새 토큰 쌍 발급
```

```python
# app/auth/desktop_strategy.py
class DesktopAuthStrategy(AuthStrategy):
    """Desktop: OAuth2 PKCE → Self-issued JWT"""

    async def authenticate(self, request: Request, **kwargs) -> AuthResult:
        # 1. Body에서 authorization_code + code_verifier 추출
        # 2. Google Token Exchange API 호출
        #    POST https://oauth2.googleapis.com/token
        #    { grant_type: "authorization_code", code, code_verifier, client_id, redirect_uri }
        # 3. 받은 id_token 검증 (Google 공개키)
        # 4. AuthResult 반환
        ...

    async def create_session(self, auth_result: AuthResult) -> dict:
        # 자체 JWT 쌍 발급
        # access_token:  exp = 1시간
        # refresh_token: exp = 30일
        # Redis에 refresh_token 저장 (Rotation 추적)
        #   key: "desktop:refresh:{user_id}:{device_id}"
        #   val: { refresh_token, device_name, created_at }
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "access_expires": access_exp,
            "refresh_expires": refresh_exp,
        }

    async def build_response(self, response_data, session_data) -> Response:
        # JSONResponse with tokens in body (쿠키 없음)
        ...

    async def logout(self, request: Request, user_id: str) -> None:
        # Redis에서 refresh_token 삭제
        # device_id 기반으로 해당 기기만 로그아웃
        ...

    async def heartbeat(self, request: Request) -> dict:
        # access_token 검증 → exp 반환
        ...

    async def refresh(self, request: Request) -> dict:
        # 1. refresh_token 검증
        # 2. Redis에서 일치 여부 확인 (Rotation 탐지)
        # 3. 새 Access + Refresh 발급
        # 4. Redis 업데이트
        # 5. 이전 refresh_token 즉시 무효화
        ...
```

### 6.4 DeviceAuthStrategy (IoT)

```
인증 흐름:
  관리자 → 대시보드에서 디바이스 등록 → API Key + Device Secret 발급
  Device → POST /auth/login/device
           Headers: X-API-Key: <api_key>
           Body: { "device_id": "...", "device_secret": "..." }
  Server → device_id + device_secret 검증 (DB 조회)
  Server → 장기 토큰 발급 (Access 24시간, Refresh 90일)

후속 요청:
  Device → Authorization: Bearer <access_token>
  Server → 자체 JWT 검증

토큰 갱신:
  Device → POST /auth/refresh/device
           Body: { "refresh_token": "..." }
  Server → 새 토큰 발급 (Rotation 없음 - IoT 환경 안정성 우선)
```

```python
# app/auth/device_strategy.py
class DeviceAuthStrategy(AuthStrategy):
    """IoT: API Key + Device Secret → Long-lived JWT"""

    async def authenticate(self, request: Request, **kwargs) -> AuthResult:
        # 1. Body에서 device_id + device_secret 추출
        # 2. DB에서 디바이스 조회 및 secret 검증
        # 3. 디바이스 활성 상태 확인
        # 4. AuthResult 반환 (user_id = device.owner_id)
        ...

    async def create_session(self, auth_result: AuthResult) -> dict:
        # 장기 토큰 발급
        # access_token:  exp = 24시간
        # refresh_token: exp = 90일
        # Redis에 디바이스 세션 저장
        #   key: "device:session:{device_id}"
        #   val: { access_token, refresh_token, owner_id, last_seen }
        ...

    async def build_response(self, response_data, session_data) -> Response:
        # JSONResponse with tokens
        ...

    async def logout(self, request: Request, user_id: str) -> None:
        # Redis에서 디바이스 세션 삭제
        ...

    async def heartbeat(self, request: Request) -> dict:
        # IoT는 heartbeat 불필요 (긴 TTL)
        # 호출 시 last_seen 업데이트 정도
        ...

    async def refresh(self, request: Request) -> dict:
        # Rotation 없이 단순 갱신 (IoT 안정성 우선)
        # refresh_token 검증 → 새 access_token만 발급
        # refresh_token 자체는 만료까지 유지
        ...
```

---

## 7. 공통 서비스 레이어

### 7.1 AuthService (비즈니스 로직)

```python
# app/services/auth_service.py
class AuthService:
    """
    인증 비즈니스 로직 - 플랫폼 무관한 공통 처리
    모든 Strategy가 이 서비스를 호출
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_user(
        self, user_id: str, email: str, name: str = None, picture: str = None
    ) -> tuple[User, bool]:
        """
        유저 조회 또는 생성

        Returns:
            (user, is_new_user)
        """
        # 1. user_id로 조회
        # 2. 있으면 → last_login 업데이트, (name, picture 갱신)
        # 3. 없으면 → 생성 + 초기 포인트 지급
        # 4. 비활성 유저면 → 복구
        ...

    async def get_user_by_id(self, user_id: str) -> User | None:
        """유저 조회"""
        ...

    async def deactivate_user(self, user_id: str) -> bool:
        """계정 비활성화 (soft delete)"""
        ...

    async def grant_signup_bonus(self, user_id: str, amount: int = 10) -> None:
        """가입 보너스 포인트 지급"""
        ...
```

### 7.2 엔드포인트에서의 사용 패턴

```python
# app/api/v1/endpoints/auth/web.py
from app.auth import get_strategy
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth - Web"])

@router.post("/login/web")
async def login_web(
    request: Request,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    strategy = get_strategy("web")

    # 1. 인증 (Firebase JWT 검증)
    auth_result = await strategy.authenticate(request)

    # 2. 비즈니스 로직 (유저 조회/생성 - 공통)
    service = AuthService(db)
    user, is_new = await service.get_or_create_user(
        user_id=auth_result.user_id,
        email=auth_result.email,
        name=auth_result.name,
        picture=auth_result.picture,
    )

    # 3. 세션 생성 (플랫폼별)
    session_data = await strategy.create_session(auth_result)

    # 4. 응답 생성 (플랫폼별)
    response_data = {
        "success": True,
        "message": "가입 완료! 10포인트 지급" if is_new else "로그인 성공",
        "user": UserResponse.model_validate(user).model_dump(),
        "is_new_user": is_new,
        "expires": session_data.get("expires") or session_data.get("access_expires"),
    }
    return await strategy.build_response(response_data, session_data)
```

**핵심: 모든 login 엔드포인트가 동일한 4단계 흐름을 따른다.**
1. `strategy.authenticate()` - 플랫폼별 인증
2. `auth_service.get_or_create_user()` - 공통 비즈니스 로직
3. `strategy.create_session()` - 플랫폼별 세션/토큰
4. `strategy.build_response()` - 플랫폼별 응답

---

## 8. API 엔드포인트 명세

### 8.1 인증 (플랫폼별)

```
POST /api/v1/auth/login/web
  Headers:
    X-API-Key: <api_key>
    Authorization: Bearer <firebase_jwt>
  Response:
    Set-Cookie: session=<session_id>; HttpOnly; Secure; SameSite=Lax
    Body: { success, user, is_new_user, expires }

POST /api/v1/auth/login/mobile
  Headers:
    X-API-Key: <api_key>
    Authorization: Bearer <firebase_jwt>
  Response:
    Body: { success, user, is_new_user, expires }

POST /api/v1/auth/login/desktop
  Headers:
    X-API-Key: <api_key>
  Body:
    { "code": "<authorization_code>", "code_verifier": "<pkce_verifier>" }
  Response:
    Body: { success, user, is_new_user, access_token, refresh_token, expires }

POST /api/v1/auth/login/device
  Headers:
    X-API-Key: <api_key>
  Body:
    { "device_id": "...", "device_secret": "..." }
  Response:
    Body: { success, device_id, owner_id, access_token, refresh_token, expires }
```

### 8.2 토큰 갱신

```
POST /api/v1/auth/refresh/desktop
  Headers:
    X-API-Key: <api_key>
  Body:
    { "refresh_token": "..." }
  Response:
    Body: { access_token, refresh_token, expires }
  Note: Refresh Token Rotation 적용

POST /api/v1/auth/refresh/device
  Headers:
    X-API-Key: <api_key>
  Body:
    { "refresh_token": "..." }
  Response:
    Body: { access_token, expires }
  Note: Rotation 미적용 (기존 refresh_token 유지)
```

### 8.3 세션 관리

```
POST /api/v1/auth/heartbeat/web
  Headers:
    X-API-Key: <api_key>
    Cookie: session=<session_id>
  Response:
    Set-Cookie: session=<session_id> (갱신)
    Body: { success, expires }
  Note: 슬라이딩 윈도우 갱신

POST /api/v1/auth/heartbeat/mobile
  Headers:
    X-API-Key: <api_key>
    Authorization: Bearer <firebase_jwt>
  Response:
    Body: { success, expires }
  Note: 검증만, 갱신 없음
```

### 8.4 공통

```
POST /api/v1/auth/logout
  Headers:
    X-API-Key: <api_key>
    X-Platform: web | mobile | desktop | device
    Authorization: Bearer <token> (mobile/desktop/device)
    Cookie: session=<id> (web)
  Response:
    Body: { success, message }

GET /api/v1/auth/me
  Headers:
    인증 헤더 (플랫폼별)
  Response:
    Body: { user_id, email, name, picture, points, ... }

DELETE /api/v1/auth/account
  Headers:
    인증 헤더 (플랫폼별)
  Response:
    Body: { success, message }
  Note: Soft delete + 모든 세션/토큰 무효화
```

---

## 9. 인증 의존성 (Dependency Injection)

```python
# app/api/v1/dependencies/api_key.py
async def verify_api_key(
    x_api_key: str = Header(..., alias="X-API-Key")
) -> str:
    """모든 요청에 필수 - API Key 검증"""
    if x_api_key != settings.API_SECRET_KEY:
        raise HTTPException(401, "Invalid API key")
    return x_api_key


# app/api/v1/dependencies/auth.py

async def verify_web_session(request: Request) -> AuthResult:
    """Web 전용 - 쿠키 세션 검증"""
    session_id = request.cookies.get("session")
    if not session_id:
        raise HTTPException(401, "No session cookie")
    session_data = await session_manager.validate_and_slide(session_id)
    if not session_data:
        raise HTTPException(401, "Session expired")
    return AuthResult(
        user_id=session_data["user_id"],
        platform="web",
        auth_type="session",
        expires=int(session_data["expires"]),
        ...
    )


async def verify_firebase_jwt(
    authorization: str = Header(...)
) -> AuthResult:
    """Mobile 전용 - Firebase JWT 검증"""
    token = _extract_bearer(authorization)
    user_data = firebase_verifier.verify(token)
    await jwt_manager.check_and_mark_used(user_data)
    return AuthResult(
        user_id=user_data["sub"],
        email=user_data.get("email"),
        platform="mobile",
        auth_type="firebase",
        expires=user_data.get("exp"),
        ...
    )


async def verify_self_jwt(
    authorization: str = Header(...)
) -> AuthResult:
    """Desktop/IoT 전용 - 자체 발급 JWT 검증"""
    token = _extract_bearer(authorization)
    payload = decode_self_jwt(token)  # HS256 or RS256
    return AuthResult(
        user_id=payload["sub"],
        platform=payload.get("platform"),
        auth_type="self_jwt",
        expires=payload["exp"],
        ...
    )


async def verify_any_platform(
    request: Request,
    x_platform: str = Header(..., alias="X-Platform"),
    authorization: Optional[str] = Header(None),
) -> AuthResult:
    """
    공통 엔드포인트용 - X-Platform 헤더로 분기
    /auth/me, /auth/logout, /auth/account 등에서 사용
    """
    if x_platform == "web":
        return await verify_web_session(request)
    elif x_platform == "mobile":
        return await verify_firebase_jwt(authorization=authorization)
    elif x_platform in ("desktop", "device"):
        return await verify_self_jwt(authorization=authorization)
    else:
        raise HTTPException(400, f"Unknown platform: {x_platform}")
```

---

## 10. Redis 키 패턴

```
# Web 세션
sess:{session_id}                       → Hash { user_id, expires, last_active, created_at }
                                          TTL: SESSION_TTL_MIN * 60

# JWT 재사용 방지 (Firebase)
jwt_used:{user_id}:{issued_at}          → String "used" | "revoked"
                                          TTL: JWT 남은 수명

# Desktop Refresh Token
desktop:refresh:{user_id}:{device_id}   → Hash { refresh_token, device_name, created_at }
                                          TTL: REFRESH_TOKEN_EXPIRE_DAYS * 86400

# IoT Device 세션
device:session:{device_id}              → Hash { access_token, refresh_token, owner_id, last_seen }
                                          TTL: DEVICE_REFRESH_EXPIRE_DAYS * 86400

# API Key → Device 매핑 (빠른 조회)
apikey:{api_key_hash}                   → String device_id
                                          TTL: 없음 (영구)
```

---

## 11. 데이터 모델 (추가/변경)

### 11.1 Device 모델 (신규)

```python
# app/models/device.py
class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    device_secret_hash: Mapped[str] = mapped_column(String(256))
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))           # "거실 센서"
    device_type: Mapped[str] = mapped_column(String(50))     # "sensor", "actuator"
    is_active: Mapped[bool] = mapped_column(default=True)
    last_seen: Mapped[datetime] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
```

### 11.2 User 모델 변경사항

기존 User 모델에 추가 필요한 필드:

```python
# 소셜 로그인 관련 (Firebase UID 저장)
firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=True, index=True)
picture: Mapped[str] = mapped_column(Text, nullable=True)
```

---

## 12. 보안 고려사항

### 12.1 API Key

- 모든 엔드포인트에 `X-API-Key` 필수 (1차 방어선)
- 키 값은 환경변수(`API_SECRET_KEY`)로 관리
- 향후 클라이언트별 API Key 분리 가능 (rate limiting 등)

### 12.2 PKCE (Desktop)

- Desktop은 client_secret을 안전하게 보관할 수 없음 (디컴파일 가능)
- PKCE (Proof Key for Code Exchange)로 authorization_code 탈취 방지
- `code_verifier`: 클라이언트가 생성한 랜덤 문자열
- `code_challenge`: SHA256(code_verifier)를 base64url 인코딩
- Google이 code와 code_verifier 매칭 검증

### 12.3 IoT Device Secret

- device_secret은 bcrypt 해싱하여 DB 저장
- 디바이스 등록 시 1회만 평문 반환, 이후 조회 불가
- 디바이스 분실/교체 시 secret 재발급 필요

### 12.4 토큰 재사용 방지

| 플랫폼 | 방식 |
|--------|------|
| Web | 서버 세션이므로 불필요 (세션 자체가 상태) |
| Mobile | JWT `iat` 기반 Redis 1회용 체크 (기존 pdf-helper-bapi 방식) |
| Desktop | Refresh Token Rotation (Redis에 현재 유효한 refresh만 저장) |
| IoT | 단순 토큰 검증 (Rotation 없음, 안정성 우선) |

### 12.5 Cookie 설정 (Web)

```python
Set-Cookie: session=<id>
  HttpOnly = True          # XSS로 JS에서 접근 불가
  Secure = True            # HTTPS만 (production)
  SameSite = Lax           # CSRF 기본 방어
  Path = /
  Max-Age = SESSION_TTL_MIN * 60 * 2   # 쿠키는 세션 TTL의 2배 (서버가 최종 판단)
```

---

## 13. 시퀀스 다이어그램

### 13.1 Web Login Flow

```
Browser          Backend              Redis           Firebase/Google
   |                |                    |                   |
   |-- POST /auth/login/web ----------->|                   |
   |   (X-API-Key, Bearer firebase_jwt) |                   |
   |                |                    |                   |
   |                |-- verify API key --|                   |
   |                |-- verify JWT ------|------------------>|
   |                |                    |    (public key)   |
   |                |<- JWT payload -----|-------------------|
   |                |                    |                   |
   |                |-- check JWT used ->|                   |
   |                |<- not used --------|                   |
   |                |-- mark JWT used -->|                   |
   |                |                    |                   |
   |                |-- get/create user  |  (PostgreSQL)     |
   |                |                    |                   |
   |                |-- destroy old sess>|                   |
   |                |-- create session ->|                   |
   |                |<- session_id ------|                   |
   |                |                    |                   |
   |<- 200 + Set-Cookie: session=xxx ---|                   |
   |   { success, user, expires }       |                   |
```

### 13.2 Desktop Login Flow (OAuth2 PKCE)

```
Desktop App      System Browser     Google OAuth      Backend           Redis
    |                  |                 |                |                |
    |-- open browser ->|                 |                |                |
    |   (auth URL +    |                 |                |                |
    |    code_challenge)|                |                |                |
    |                  |-- GET /auth --->|                |                |
    |                  |<- login page ---|                |                |
    |                  |-- user login -->|                |                |
    |                  |<- redirect -----|                |                |
    |                  |   ?code=xxx     |                |                |
    |<- code callback -|                 |                |                |
    |   (localhost:9876)                 |                |                |
    |                                    |                |                |
    |-- POST /auth/login/desktop --------|--------------->|                |
    |   { code, code_verifier }          |                |                |
    |                                    |                |                |
    |                                    |   POST /token  |                |
    |                                    |<---------------|                |
    |                                    |-- id_token --->|                |
    |                                    |                |                |
    |                                    |                |-- create JWT ->|
    |                                    |                |-- store refresh>|
    |                                    |                |                |
    |<- { access_token, refresh_token } -|----------------|                |
```

---

## 14. 마이그레이션 가이드 (pdf-helper-bapi → 신규 구조)

### Phase 1: 인프라 구축
1. `app/auth/` 모듈 생성 (base.py, firebase_verifier.py, jwt_manager.py, session_manager.py)
2. pdf-helper-bapi의 유틸을 정리하여 이식:
   - `firebase_jwt_verifier.py` → `app/auth/firebase_verifier.py`
   - `jwt_manager.py` → `app/auth/jwt_manager.py`
   - `session_manager.py` → `app/auth/session_manager.py`
3. AuthStrategy 추상 클래스 및 팩토리 구현

### Phase 2: Web + Mobile (기존 기능 대체)
1. `WebAuthStrategy` 구현
2. `MobileAuthStrategy` 구현
3. `AuthService.get_or_create_user()` 구현
4. 엔드포인트 작성: `/auth/login/web`, `/auth/login/mobile`
5. 의존성 작성: `verify_web_session`, `verify_firebase_jwt`, `verify_any_platform`
6. 기존 pdf-helper-bapi의 테스트 케이스로 검증

### Phase 3: Desktop
1. Google OAuth2 PKCE 토큰 교환 로직 구현
2. 자체 JWT 발급/검증 로직 구현
3. `DesktopAuthStrategy` 구현
4. Refresh Token Rotation 구현
5. 엔드포인트 작성: `/auth/login/desktop`, `/auth/refresh/desktop`

### Phase 4: IoT
1. Device 모델 생성 및 마이그레이션
2. 디바이스 등록 관리 API (별도 admin 엔드포인트)
3. `DeviceAuthStrategy` 구현
4. 엔드포인트 작성: `/auth/login/device`, `/auth/refresh/device`

---

## 15. 환경변수 목록

```env
# 공통
API_SECRET_KEY=                     # X-API-Key 검증용
SECRET_KEY=                         # 자체 JWT 서명키 (Desktop/IoT용)
ENVIRONMENT=development             # development | production

# Database
DATABASE_URL=postgresql+asyncpg://...

# Redis
REDIS_URL=redis://localhost:6379

# Firebase (Web/Mobile)
FIREBASE_PROJECT_ID=
FIREBASE_JWKS_URI=https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com

# Google OAuth (Desktop)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=               # PKCE에서는 optional이지만 서버에서 token exchange 시 필요

# Session (Web)
SESSION_TTL_MIN=30
SESSION_PREFIX=sess
COOKIE_SECURE=true
COOKIE_SAMESITE=lax

# Token TTL
ACCESS_TOKEN_EXPIRE_MINUTES=60      # Desktop access token
REFRESH_TOKEN_EXPIRE_DAYS=30        # Desktop refresh token
DEVICE_ACCESS_EXPIRE_HOURS=24       # IoT access token
DEVICE_REFRESH_EXPIRE_DAYS=90       # IoT refresh token
```

---

## 16. 참고: pdf-helper-bapi에서 가져올 코드

| 원본 파일 | 용도 | 이식 대상 | 변경 필요 |
|-----------|------|-----------|-----------|
| `firebase_jwt_verifier.py` | Firebase JWT 검증 | `app/auth/firebase_verifier.py` | 디버그 코드 제거, 에러 처리 정리 |
| `jwt_manager.py` | JWT 재사용 방지 | `app/auth/jwt_manager.py` | HTTPException 대신 커스텀 예외 사용 |
| `session_manager.py` | Redis 세션 관리 | `app/auth/session_manager.py` | `await_maybe` 제거 (async 통일) |
| `response_helpers.py` | 쿠키 응답 생성 | `WebAuthStrategy.build_response()` 내부로 흡수 | 하드코딩 제거 |
| `auth_router.py` login() | 비즈니스 로직 | `AuthService.get_or_create_user()` | 플랫폼 분기 제거, 순수 비즈니스 로직만 |
| `dependencies/auth.py` | 인증 미들웨어 | `app/api/v1/dependencies/auth.py` | 전략별 분리 |
