# Security Implementation TODO - Min-Minisaas Backend

**Status:** Planning
**Last Updated:** Feb 11, 2026
**Overall Progress:** 0/7 Tasks

---

## 📋 Task Overview

This document outlines 7 security enhancement tasks identified in the auth-architecture-design.md review. Tasks are organized by priority level (P1 = Critical, P2 = Important, P3 = Enhancement).

**Security Goals:**
- Reduce overall risk from **7/10 → 3/10**
- Implement OWASP Top 10 defenses
- Enable scalable, multi-platform security

---

## 🔴 Priority 1 - CRITICAL (Do First)

### Task 1: Implement Refresh Token Reuse Detection (Desktop)

**Status:** ⬜ Not Started
**Risk Level:** 🔴 CRITICAL (Risk: 60% → 5% after completion)
**File Owner:** `app/auth/desktop_strategy.py`, `app/auth/jwt_manager.py`

#### Problem
- Desktop platform uses Refresh Token Rotation (RTR) but lacks **reuse detection**
- If a refresh token is intercepted and replayed, both attacker and legitimate user get new tokens
- System cannot detect this attack → attacker silently maintains access

#### Current Behavior
```python
# VULNERABLE: No detection of simultaneous token generation
async def refresh(self, request: Request) -> dict:
    token = extract_token_from_request(request)
    payload = decode_token(token)
    # ❌ No check: "Did I already issue a new token for this refresh_token?"
    new_token = self.jwt_manager.generate_token(payload)
    return {"access_token": new_token, "refresh_token": new_refresh_token}
```

#### Implementation Checklist

- [ ] **Step 1: Update JWT Manager Schema**
  - Add `RefreshTokenHistory` model to track issued refresh tokens
  - Fields: `user_id`, `old_refresh_token_hash`, `new_refresh_token_hash`, `issued_at`, `generation_count`
  - Store in Redis with TTL = REFRESH_TOKEN_EXPIRE_DAYS

- [ ] **Step 2: Implement Reuse Detection Logic**
  - When `refresh()` is called:
    1. Check if `old_refresh_token` was already used
    2. If used: Revoke ALL tokens for this user (security breach response)
    3. If not used: Record the token exchange + issue new refresh token
  - Location: `app/auth/jwt_manager.py` method `detect_and_log_refresh_reuse()`

- [ ] **Step 3: Update Desktop Strategy**
  - Call `jwt_manager.detect_and_log_refresh_reuse()` in `refresh()` method
  - On reuse detection: raise `HTTPException(401, "Suspicious activity detected. Re-authenticate required.")`
  - Trigger user notification (future: email alert)

- [ ] **Step 4: Add User Alert Mechanism**
  - When token reuse is detected:
    - Log security event: `SecurityLog.create(user_id, event_type='TOKEN_REUSE_DETECTED')`
    - Optionally: Send email to user (future integration)

#### Testing Criteria
```python
# Test case: test_desktop_token_reuse_detection
1. User logs in → get refresh_token_1
2. Attacker uses refresh_token_1 → gets refresh_token_2
3. User also uses refresh_token_1 → should fail with "Suspicious activity"
4. All user tokens should be revoked
5. User must re-authenticate
```

#### Files to Modify
- `app/auth/jwt_manager.py` - Add `detect_and_log_refresh_reuse()` method
- `app/auth/desktop_strategy.py` - Call detection in `refresh()`
- `app/models/security_log.py` - NEW: Create SecurityLog model
- `tests/test_auth_endpoints.py` - Add reuse detection test

#### Estimated Effort
⏱️ **4-6 hours**

---

### Task 2: Prevent Session Fixation Attack (Web)

**Status:** ⬜ Not Started
**Risk Level:** 🔴 HIGH (Affects: Web platform only)
**File Owner:** `app/auth/session_manager.py`, `app/auth/web_strategy.py`

#### Problem
- Web platform uses server-side session (Redis)
- If attacker pre-sets a session ID: `session=attacker_chosen_id`
- User logs in with that session ID → attacker can use same ID to access user account

#### Current Behavior
```python
# VULNERABLE: Uses same session ID across login
async def create_session(self, auth_result: AuthResult) -> dict:
    session_id = request.cookies.get("session")  # ❌ Attacker might have set this
    if not session_id:
        session_id = generate_id()

    await session_manager.set(session_id, user_data)
    return {"session_id": session_id}
```

#### Implementation Checklist

- [ ] **Step 1: Modify Web Strategy create_session()**
  - Always generate a NEW session ID after login (ignore old one)
  - Destroy old session if it exists
  - Return new session ID in Set-Cookie header

- [ ] **Step 2: Update Session Manager**
  - Add `destroy_session(session_id)` method if not exists
  - Ensure Redis key is deleted completely

- [ ] **Step 3: Implementation Code**
  ```python
  # In web_strategy.py
  async def create_session(self, auth_result: AuthResult) -> dict:
      # 1. Get old session (if any)
      old_session_id = request.cookies.get("session")

      # 2. Destroy it (session fixation prevention)
      if old_session_id:
          await self.session_manager.destroy(old_session_id)

      # 3. Generate new session ID (always fresh)
      new_session_id = self.session_manager.generate_secure_id()

      # 4. Create new session
      await self.session_manager.set(
          new_session_id,
          {
              "user_id": auth_result.user_id,
              "expires": int(time()) + self.session_ttl,
              "created_at": int(time())  # Track when session was created
          }
      )

      return {"session_id": new_session_id}
  ```

- [ ] **Step 4: Update Tests**
  - Test: "Old session ID is not reusable after login"
  - Test: "New session ID is returned after login"

#### Testing Criteria
```python
# Test case: test_web_session_fixation_prevention
1. Attacker sets cookie: session=ATTACKER_ID
2. User logs in
3. Verify: ATTACKER_ID is destroyed (Redis check)
4. Verify: New session ID is returned
5. Verify: Only new session ID works for accessing /auth/me
```

#### Files to Modify
- `app/auth/web_strategy.py` - Update `create_session()` method
- `app/auth/session_manager.py` - Ensure `destroy()` method exists
- `tests/test_auth_endpoints.py` - Add session fixation prevention test

#### Estimated Effort
⏱️ **2-3 hours**

---

## 🟡 Priority 2 - IMPORTANT (Do Next)

### Task 3: Add Device Secret Rotation & Rate Limiting (IoT)

**Status:** ⬜ Not Started
**Risk Level:** 🔴 CRITICAL (Device exposed = full account compromise)
**File Owner:** `app/auth/device_strategy.py`, `app/models/device.py`

#### Problem
- IoT devices store `device_secret` in hardware (easily extracted if device compromised)
- Once secret is compromised, attacker has permanent access
- No mechanism to detect or limit brute force attacks
- No way to revoke/rotate compromised secrets

#### Current Behavior
```python
# app/api/v1/endpoints/auth/device.py
# ❌ No rate limiting on failed attempts
# ❌ No secret rotation mechanism
# ❌ No breach detection

if not pwd_context.verify(device_secret, device.device_secret_hash):
    raise HTTPException(401, "Invalid device secret")
```

#### Implementation Checklist

- [ ] **Step 1: Add Failed Login Tracking**
  - Track failed attempts per device_id in Redis
  - Key: `device:failed_login:{device_id}`
  - Increment on failed login, reset on successful login
  - TTL: 1 hour

- [ ] **Step 2: Implement Rate Limiting**
  - After 5 failed attempts in 1 hour: Lock device temporarily
  - Lock duration: 15 minutes
  - Set Redis key: `device:locked:{device_id}` with TTL=15min
  - Return: `HTTPException(429, "Device temporarily locked. Try again in 15 minutes")`

- [ ] **Step 3: Add Secret Rotation Capability**
  - Add endpoint: `POST /api/v1/auth/device/{device_id}/rotate-secret`
  - Requires: Valid device_id + old device_secret
  - Returns: New device_secret
  - Store new secret hash in Device model
  - Log rotation event

- [ ] **Step 4: Implementation Code**
  ```python
  # In device_strategy.py or device.py endpoint

  DEVICE_FAILED_LOGIN_LIMIT = 5
  DEVICE_LOCKOUT_MINUTES = 15

  async def login_device(request: Request, db: AsyncSession):
      body = await request.json()
      device_id = body.get("device_id")
      device_secret = body.get("device_secret")

      # 1. Check if device is locked
      is_locked = await cache.get(f"device:locked:{device_id}")
      if is_locked:
          raise HTTPException(429, "Device temporarily locked")

      # 2. Get device from DB
      device = await db.execute(...)

      # 3. Verify secret
      if not pwd_context.verify(device_secret, device.device_secret_hash):
          # Increment failed counter
          failed_count = await cache.incr(f"device:failed_login:{device_id}")
          if failed_count >= DEVICE_FAILED_LOGIN_LIMIT:
              # Lock device
              await cache.set(
                  f"device:locked:{device_id}",
                  "locked",
                  ex=DEVICE_LOCKOUT_MINUTES * 60
              )
          raise HTTPException(401, "Invalid secret")

      # 4. Reset failed counter on success
      await cache.delete(f"device:failed_login:{device_id}")

      # Continue with normal login flow...
  ```

- [ ] **Step 5: Add Rotation Endpoint**
  ```python
  @router.post("/device/{device_id}/rotate-secret")
  async def rotate_device_secret(
      device_id: str,
      request: Request,
      db: AsyncSession = Depends(get_db),
      api_key: str = Depends(verify_api_key)
  ):
      body = await request.json()
      old_secret = body.get("device_secret")  # Current secret for verification

      # 1. Verify old secret
      device = await get_device(db, device_id)
      if not pwd_context.verify(old_secret, device.device_secret_hash):
          raise HTTPException(401, "Invalid secret")

      # 2. Generate new secret
      new_secret = secrets.token_urlsafe(32)
      new_hash = pwd_context.hash(new_secret)

      # 3. Store new hash
      device.device_secret_hash = new_hash
      device.secret_rotated_at = datetime.now()
      await db.commit()

      # 4. Log rotation
      await SecurityLog.create(
          db,
          user_id=device.owner_id,
          event_type='DEVICE_SECRET_ROTATED',
          device_id=device_id
      )

      return {
          "success": True,
          "device_id": device_id,
          "new_secret": new_secret,  # Only shown once!
          "message": "Secret rotated. Save the new secret securely."
      }
  ```

#### Testing Criteria
```python
# Test 1: test_device_rate_limiting
1. Make 5 failed login attempts with wrong secret
2. 6th attempt should return 429 (Locked)
3. Wait 15 minutes (or mock time)
4. 7th attempt should succeed

# Test 2: test_device_secret_rotation
1. Device with old_secret rotates to new_secret
2. Old secret no longer works
3. New secret works
4. SecurityLog entry created
```

#### Files to Modify
- `app/api/v1/endpoints/auth/device.py` - Add rate limiting + rotation endpoint
- `app/models/device.py` - Add `secret_rotated_at` field
- `app/models/security_log.py` - Ensure SecurityLog model exists
- `tests/test_auth_endpoints.py` - Add rate limiting & rotation tests

#### Estimated Effort
⏱️ **5-7 hours** (includes testing)

---

### Task 4: Unified Error Response Format (All Platforms)

**Status:** ⬜ Not Started
**Risk Level:** 🟡 MEDIUM (Info leakage, low impact)
**File Owner:** `app/auth/*/strategy.py`, `app/api/v1/dependencies/auth.py`

#### Problem
- Different platforms return different error messages
- Example:
  - Web: "이메일 또는 비밀번호 오류"
  - Mobile: "Invalid credentials"
  - Desktop: "Authentication failed"
- Allows attackers to fingerprint which platform/backend is used

#### Current Behavior
```python
# Web (legacy.py)
raise HTTPException(401, "이메일 또는 비밀번호 오류")

# Desktop (desktop.py)
raise HTTPException(400, "Missing code")

# Device (device.py)
raise HTTPException(401, "Invalid device secret")
```

#### Implementation Checklist

- [ ] **Step 1: Create Standardized Error Response Class**
  ```python
  # In app/schemas/error.py
  class AuthErrorResponse(BaseModel):
      success: bool = False
      error_code: str  # "INVALID_CREDENTIALS", "MISSING_FIELD", etc.
      message: str    # Generic message only
      status_code: int

  ERROR_MESSAGES = {
      "INVALID_CREDENTIALS": "Authentication failed",
      "MISSING_FIELD": "Missing required field",
      "INVALID_TOKEN": "Invalid or expired token",
      "DEVICE_LOCKED": "Too many attempts. Try again later.",
      "USER_NOT_FOUND": "Authentication failed",
      "SESSION_EXPIRED": "Session expired. Please login again",
  }
  ```

- [ ] **Step 2: Create Custom Exception Handler**
  ```python
  # In app/core/exceptions.py
  class AuthException(Exception):
      def __init__(self, error_code: str, status_code: int = 401):
          self.error_code = error_code
          self.status_code = status_code
          self.message = ERROR_MESSAGES.get(error_code, "Unknown error")

  @app.exception_handler(AuthException)
  async def auth_exception_handler(request: Request, exc: AuthException):
      return JSONResponse(
          status_code=exc.status_code,
          content={
              "success": False,
              "error_code": exc.error_code,
              "message": exc.message
          }
      )
  ```

- [ ] **Step 3: Update All Strategies**
  - Replace all `raise HTTPException(401, "specific message")` with `raise AuthException("INVALID_CREDENTIALS")`
  - Files:
    - `app/auth/web_strategy.py`
    - `app/auth/mobile_strategy.py`
    - `app/auth/desktop_strategy.py`
    - `app/auth/device_strategy.py`

- [ ] **Step 4: Update All Endpoints**
  - Files:
    - `app/api/v1/endpoints/auth/legacy.py`
    - `app/api/v1/endpoints/auth/web.py`
    - `app/api/v1/endpoints/auth/mobile.py`
    - `app/api/v1/endpoints/auth/desktop.py`
    - `app/api/v1/endpoints/auth/device.py`
    - `app/api/v1/dependencies/auth.py`

#### Testing Criteria
```python
# Test: test_error_response_unified_format
1. Invalid email/password → {"error_code": "INVALID_CREDENTIALS", "message": "Authentication failed"}
2. Missing field → {"error_code": "MISSING_FIELD", "message": "Missing required field"}
3. Invalid token → {"error_code": "INVALID_TOKEN", "message": "Invalid or expired token"}
4. All platforms return same error format
```

#### Files to Modify
- `app/schemas/error.py` - NEW
- `app/core/exceptions.py` - NEW: Create `AuthException` handler
- All `app/auth/*_strategy.py` files - Replace HTTPException with AuthException
- All `app/api/v1/endpoints/auth/*.py` files - Replace HTTPException with AuthException
- `app/api/v1/dependencies/auth.py` - Standardize errors
- `tests/test_auth_endpoints.py` - Verify error format consistency

#### Estimated Effort
⏱️ **3-4 hours** (mostly find-replace + testing)

---

## 🟢 Priority 3 - ENHANCEMENT (Nice to Have)

### Task 5: Add CSRF Token for Sensitive Operations

**Status:** ⬜ Not Started
**Risk Level:** 🟢 LOW (Already mitigated by SameSite=Lax)
**File Owner:** `app/api/v1/endpoints/auth/common.py`

#### Purpose
- Extra layer of protection for sensitive operations (logout, account deletion)
- Even though SameSite=Lax provides protection, CSRF token adds defense-in-depth

#### Implementation
- [ ] Add `X-CSRF-Token` header requirement for `POST /logout`, `DELETE /account`
- [ ] Generate CSRF token on `/auth/me` GET request
- [ ] Validate token on sensitive POST/DELETE requests

#### Estimated Effort: 2 hours

---

### Task 6: Implement mTLS for Device/IoT (Optional)

**Status:** ⬜ Not Started
**Risk Level:** 🔴 CRITICAL (Defense against hardware compromise)
**Note:** This is a DevOps/infrastructure task, not backend code

#### Purpose
- Use certificate-based authentication instead of (or in addition to) device_secret
- Each device gets unique X.509 certificate
- Client certificate authentication on TLS layer

#### Considerations
- Requires certificate management infrastructure
- Certificate rotation, revocation (CRL/OCSP)
- Works well for dedicated IoT networks
- More complex but very secure

#### Estimated Effort: 16+ hours (infrastructure setup)

---

### Task 7: Hardware Security Module (HSM) for Secret Storage

**Status:** ⬜ Not Started
**Risk Level:** 🔴 CRITICAL (Best protection against hardware attacks)
**Note:** This requires hardware investment

#### Purpose
- Store device secrets in Trusted Execution Environment (TEE)
- Even if device is physically attacked, secrets remain protected
- Used in enterprise/high-security deployments

#### Examples
- ARM TrustZone (mobile devices)
- Intel SGX (server CPUs)
- Hardware security modules (HSMs)

#### Estimated Effort: 20+ hours (requires hardware testing)

---

## 📊 Implementation Status Summary

```
Priority 1 (CRITICAL):
  [ ] Task 1: Token Reuse Detection (Desktop)      [0/4 steps]
  [ ] Task 2: Session Fixation Prevention (Web)    [0/4 steps]

Priority 2 (IMPORTANT):
  [ ] Task 3: Device Secret Rotation (IoT)         [0/5 steps]
  [ ] Task 4: Unified Error Responses (All)        [0/4 steps]

Priority 3 (ENHANCEMENT):
  [ ] Task 5: CSRF Token (Optional)                [0/3 steps]
  [ ] Task 6: mTLS for IoT (Infrastructure)        [Not started]
  [ ] Task 7: HSM Secret Storage (Infrastructure)  [Not started]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OVERALL PROGRESS: 0/7 tasks | 0% complete
ESTIMATED TIME: 14-20 hours (P1 + P2 only)
TARGET RISK LEVEL: 7/10 → 3/10
```

---

## 🚀 How to Use This Document

**For AI Assistant:**
1. Pick one task from Priority 1
2. Read the "Problem" section to understand the vulnerability
3. Follow the "Implementation Checklist" step-by-step
4. Verify with "Testing Criteria"
5. Move to next task

**For Developers:**
1. P1 tasks should be completed before production
2. P2 tasks should be completed within 1 sprint
3. P3 tasks are optional but recommended

---

## 📝 References

- **Security Analysis:** `/Users/nenpa/.claude/projects/-Users-nenpa-Development-MyProjects-min-minisaas-backend/memory/MEMORY.md`
- **Architecture Design:** `auth-architecture-design.md`
- **Test Framework:** `tests/conftest.py` (already has mocking infrastructure)
- **Existing Tests:** `tests/test_auth_endpoints.py`, `tests/test_auth_infrastructure.py`

---

**Last Updated:** Feb 11, 2026
**Next Review:** After completing Priority 1 tasks
