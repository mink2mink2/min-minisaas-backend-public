# V/30 — 보안 검토 체크리스트 (Security Review)

> 코드 PR 전 반드시 이 체크리스트를 확인한다.
> API 추가/변경 시 해당 항목을 체크하고 서명/날짜를 남긴다.

---

## 인증/인가 (Authentication & Authorization)

- [ ] 모든 엔드포인트에 인증이 적용되어 있다 (공개 엔드포인트는 명시적으로 예외 처리)
- [ ] 공개 엔드포인트 목록이 최신 상태이다:
  - `POST /api/v1/auth/login/google`
  - `POST /api/v1/auth/login/kakao`
  - `POST /api/v1/auth/login/naver`
  - `GET /api/v1/board/posts` (비인증 조회 허용)
  - `GET /api/v1/board/posts/{id}` (비인증 조회 허용)
  - `GET /api/v1/blogs` (비인증 조회 허용)
  - `GET /api/v1/blogs/{id}` (비인증 조회 허용)
  - `GET /health`
- [ ] 리소스 소유자 확인이 적용되어 있다 (예: 내 게시글만 수정/삭제 가능)
- [ ] 관리자 권한 확인이 필요한 엔드포인트에 `is_admin` 체크가 있다
- [ ] JWT 만료시간이 설정되어 있다 (현재: 24시간)
- [ ] `get_current_user` 의존성이 보호 엔드포인트에 올바르게 적용되어 있다

---

## Rate Limiting

- [ ] 공개 엔드포인트에 Rate Limiting이 적용되어 있다 (기본 60 req/min per IP)
- [ ] 로그인 엔드포인트에 Rate Limiting이 적용되어 있다 (10 req/min per IP)
- [ ] 게시글 작성에 Rate Limiting이 적용되어 있다 (10개/분 per user)
- [ ] 댓글 작성에 Rate Limiting이 적용되어 있다 (1개/초 per user)
- [ ] Rate Limit 초과 시 HTTP 429와 `Retry-After` 헤더를 반환한다

---

## 민감정보 보호 (Sensitive Data)

- [ ] 민감정보가 로그에 출력되지 않는다:
  - [ ] JWT 토큰
  - [ ] OAuth 액세스 토큰 (Kakao, Naver)
  - [ ] Firebase ID Token
  - [ ] DATABASE_URL (비밀번호 포함)
  - [ ] 사용자 이메일 (로그 레벨 WARNING 이하에서)
- [ ] `.env` 파일이 `.gitignore`에 포함되어 있다
- [ ] Firebase 서비스 계정 JSON이 Git에 커밋되지 않았다
- [ ] `secrets/` 디렉토리가 `.gitignore`에 포함되어 있다
- [ ] 환경변수 예시 파일(`.env.example`)에 실제 값이 없다

---

## Coin Simulator Proxy/Cache 보안

- [x] `LOCAL_COIN_API_BASE_URL`은 코드상 환경변수로만 관리된다
- [x] Coin simulator upstream URL을 관리자 UI/DB 설정으로 임의 변경할 수 없다
- [ ] `LOCAL_COIN_API_KEY` 또는 `LOCAL_COIN_API_BEARER_TOKEN`이 운영 환경에 설정되어 있다
- [x] upstream 인증 헤더가 애플리케이션 로그/에러 응답에 노출되지 않는다
- [x] `GET /api/v1/coin-simulator/dashboard`는 `data_source`(`live`/`cache`/`mock`)를 명시한다
- [x] `mock` 또는 `cache` 상태를 live와 혼동하지 않도록 notice/배너가 유지된다
- [x] `POST /api/v1/coin-simulator/start`, `POST /stop`, `PUT /settings`는 superuser만 가능하다
- [x] control endpoint 호출 시 감사 로그를 남긴다:
  - [x] 요청자 식별자
  - [x] action(start/stop/settings)
  - [x] 성공/실패 여부
  - [x] 실행 시각
- [x] control endpoint에 사용자별 rate limit이 적용되어 있다 (현재: 5 req/min)
- [x] upstream timeout이 짧게 설정되어 있다 (현재 기본값: 5초)
- [ ] 잘못된 upstream 응답은 검증 후 캐시하며, 비정상 응답을 장기 캐시하지 않는다
- [x] `COIN_SIMULATOR_CACHE_TTL_SECONDS`는 짧게 유지된다 (현재 기본값: 5초)
- [ ] production에서 backend가 접근 가능한 upstream host/port가 coinbot로 제한되어 있다
- [ ] remote 운영 환경에서는 backend↔coinbot 통신이 private network 또는 TLS로 보호된다

### Coin Simulator 보안 메모

- 현재 구조는 앱이 coinbot을 직접 호출하지 않고 backend가 proxy/cache 역할을 수행한다.
- 따라서 주요 위험은 SSRF, control endpoint 오남용, upstream secret 노출, stale cache 오인이다.
- URL 동적 변경 기능을 추가할 경우 allowlist 검증 없이 배포하지 않는다.
- 2026-03-06 기준 코드 검수 결과:
  - 구현 완료: superuser gate, mock/cache/live 구분, control audit log, control rate limit, 짧은 timeout/TTL
  - 운영 확인 필요: upstream secret 주입, TLS/private network, host/port 접근 제한

---

## SQL Injection 방지

- [ ] 모든 DB 쿼리에 SQLAlchemy ORM 또는 파라미터화 쿼리를 사용한다
- [ ] `text()` 또는 raw SQL을 사용하는 경우, 파라미터 바인딩이 적용되어 있다
- [ ] 사용자 입력이 SQL 쿼리에 직접 삽입되지 않는다

```python
# ✅ 올바른 패턴
result = await db.execute(
    select(BoardPost).where(BoardPost.title.ilike(f"%{search}%"))
)

# ✅ raw SQL 사용 시
result = await db.execute(
    text("SELECT * FROM board_posts WHERE title ILIKE :search"),
    {"search": f"%{search}%"}
)

# ❌ 절대 금지
result = await db.execute(f"SELECT * FROM board_posts WHERE title ILIKE '%{search}%'")
```

---

## XSS 방지

- [ ] 응답 데이터가 Pydantic 스키마를 통해 반환된다 (자동 이스케이핑)
- [ ] HTML을 직접 렌더링하는 엔드포인트가 없다
- [ ] 사용자 입력이 그대로 응답에 포함되는 경우 이스케이핑 처리가 되어 있다

---

## CORS 설정

- [ ] `ALLOWED_ORIGINS` 환경변수가 설정되어 있다
- [ ] Production에서 와일드카드 (`*`) CORS를 허용하지 않는다
- [ ] CORS 허용 Origin 목록이 최소 권한 원칙을 따른다

```python
# app/main.py CORS 설정 예시
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # 명시적 목록
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

## OAuth 보안

- [ ] OAuth 서버사이드 검증이 적용되어 있다 (클라이언트 토큰을 서버에서 재검증)
- [ ] Kakao Access Token을 카카오 API(`/v2/user/me`)로 검증한다
- [ ] Naver Access Token을 네이버 API(`/v1/nid/me`)로 검증한다
- [ ] Google ID Token을 Firebase Admin SDK로 검증한다
- [ ] OAuth 클라이언트 시크릿이 환경변수로만 관리된다 (코드에 하드코딩 없음)

---

## Production 설정

- [ ] `PRODUCTION=true` 환경변수가 설정된 경우 `/docs` 비활성화되어 있다
- [ ] `PRODUCTION=true` 환경변수가 설정된 경우 `/redoc` 비활성화되어 있다
- [ ] Debug 모드가 비활성화되어 있다 (`DEBUG=false`)
- [ ] HTTPS가 강제되어 있다 (Cloud Run 기본 설정 또는 리다이렉트)
- [ ] 에러 응답에 스택 트레이스가 포함되지 않는다

```python
# main.py — Production에서 Swagger 비활성화
app = FastAPI(
    docs_url=None if settings.PRODUCTION else "/docs",
    redoc_url=None if settings.PRODUCTION else "/redoc",
    openapi_url=None if settings.PRODUCTION else "/openapi.json",
)
```

---

## WebSocket 보안

- [ ] WebSocket 연결 시 JWT 토큰 검증이 수행된다 (쿼리 파라미터 또는 첫 메시지)
- [ ] 유효하지 않은 토큰으로 WebSocket 연결 시 `4001` 코드로 거부한다
- [ ] 채팅방 참여자가 아닌 사용자의 WebSocket 연결을 거부한다

---

## 데이터 격리

- [ ] 사용자 A의 데이터가 사용자 B에게 노출되지 않는다:
  - [ ] 알림 목록: `WHERE user_id = current_user.id`
  - [ ] FCM 토큰: `WHERE user_id = current_user.id`
  - [ ] 채팅 메시지: 참여자 확인 후만 조회 가능
- [ ] 삭제된 리소스(`is_deleted=True`)가 목록 조회에서 제외된다

---

## 보안 체크리스트 서명

새 기능 또는 보안 관련 변경 후 아래 표를 갱신한다:

| 날짜 | 변경 내용 | 체크 완료 | 담당자 |
|------|----------|---------|--------|
| 2026-03-06 | Coin simulator proxy/cache 보안 체크리스트 추가 | ✅ SSRF/secret/control/cache 점검 항목 문서화 | Codex |
| 2026-03-06 | Coin simulator proxy/cache API 추가 | ✅ 인증, superuser 제어, local API secret env 확인 | Codex |
| 2026-03-01 | Push API 추가 | ✅ 전체 항목 확인 | mike |
| 2026-02-22 | Blog API 추가 | ✅ 전체 항목 확인 | mike |
| 2026-02-18 | Board API 추가 | ✅ 전체 항목 확인 | mike |
| 2026-02-11 | Auth + Chat API 최초 구현 | ✅ 전체 항목 확인 | mike |

---

## 보안 도구 실행

```bash
# 의존성 취약점 스캔
pip audit

# 코드 보안 스캔 (bandit)
bandit -r app/ -ll

# 환경변수 누락 확인
python scripts/check_secrets.py

# OWASP 의존성 체크 (선택)
dependency-check --project minisaas --scan .
```

---

## 알려진 보안 제한사항 (Technical Debt)

| 항목 | 위험도 | 계획 |
|------|--------|------|
| Refresh Token 미구현 | 중간 | Task 8 이후 추가 |
| JWT 블랙리스트 미구현 | 중간 | Task 8 이후 추가 |
| WebSocket 멀티 인스턴스 | 낮음 | 스케일 아웃 시 구현 |
| Device Attestation 미구현 | 낮음 | 장기 로드맵 |
