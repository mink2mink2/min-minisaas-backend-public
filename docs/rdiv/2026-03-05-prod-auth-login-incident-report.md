# Production Incident Report — Auth/Login/Redis (2026-03-05)

## Scope
- Environment: Cloud Run production
- Project: `min-minisaas-487110`
- Region: `asia-northeast1` (Tokyo)
- Service: `min-minisaas-backend`

## Executive Summary
- 로그인 장애는 단일 원인이 아니라 순차적으로 3개가 겹쳐 발생했다.
1. `Invalid API key` (Secret 개행 문자 포함)
2. `Invalid audience` (Firebase project id Secret 개행 문자 포함)
3. `500 Internal Server Error` (Redis 연결 reset 예외 미처리)

- 최종적으로 아래까지 완료:
1. API key/Firebase audience 문제 해소
2. Redis 예외 시 500 방지 코드 반영
3. Redis TLS(`rediss://`) 전환 완료

## Timeline (KST)
1. FlutterFire 재정렬 및 앱 빌드 수행 (`1.0.5+4`)
2. `/auth/login/mobile` 401 분석 결과: `Invalid API key`
3. Cloud Run Secret raw bytes 확인: `API_SECRET_KEY` 끝에 `0a`(newline) 발견
4. newline 없는 새 Secret 버전 생성 + Cloud Run revision 롤링
5. 이후 401 원인 변경: `Invalid audience`
6. `FIREBASE_PROJECT_ID` Secret에도 trailing newline 확인/수정 + revision 롤링
7. 이후 로그인 경로에서 500 발생, 로그에서 Redis `Connection reset by peer` 확인
8. `jwt_manager`에 Redis 예외 fail-open 보호 로직 추가/배포
9. 운영 Redis URL 점검 결과 TLS 미적용(`redis://...:6380`) 확인
10. `REDIS_URL`을 `rediss://...:6380/1`로 변경 + revision 롤링

## Incident Details

### 1) Invalid API key (401)
- Symptom:
  - `POST /api/v1/auth/login/mobile` -> 401
  - Response body: `{"detail":"Invalid API key"}`
- Root cause:
  - Secret Manager `API_SECRET_KEY` 값 끝에 newline 포함
- Action:
  - newline 제거한 새 버전 발급
  - Cloud Run 재배포로 latest 반영
- Result:
  - `Invalid API key` 재발 없음

### 2) Invalid audience (401)
- Symptom:
  - 서버 로그: `Firebase JWT verification failed: Invalid audience`
- Root cause:
  - Secret Manager `FIREBASE_PROJECT_ID` 끝에 newline 포함
  - audience 비교 시 `min-minisaas\n`로 평가됨
- Action:
  - `FIREBASE_PROJECT_ID` newline 제거 버전 발급
  - Cloud Run 재배포
- Result:
  - `Invalid audience` 재발 없음

### 3) Redis connection reset -> 500
- Symptom:
  - `/auth/login/mobile` 500
  - stacktrace: `redis.asyncio ... ConnectionResetError: [Errno 104]`
- Root cause:
  - JWT replay check(`cache.get/set`)에서 Redis 예외가 상위로 전파됨
- Action:
  - `app/core/auth/jwt_manager.py`에 Redis 예외 보호 추가
  - 인증 플로우 fail-open 처리(운영 연속성 우선)
- Result:
  - Redis 순간 장애 시 auth API 500 방지

### 4) Production Redis TLS 미적용
- Symptom:
  - 배포 `REDIS_URL`이 `redis://redis.atg.re.kr:6380/1`
- Root cause:
  - 운영 URL 스킴이 TLS 스킴(`rediss`)이 아님
- Action:
  - Secret `REDIS_URL` -> `rediss://redis.atg.re.kr:6380/1` 변경
  - Cloud Run 재배포
- Result:
  - 운영 Redis TLS 적용 완료

### 5) Postgres catalog mismatch (`minisaas_db` not found)
- Symptom:
  - `/auth/login/mobile` 호출 시 500
  - stacktrace tail: `asyncpg.exceptions.InvalidCatalogNameError: database "minisaas_db" does not exist`
- Root cause (current):
  - `DATABASE_URL`의 DB 이름이 실제 PostgreSQL catalog와 불일치 가능성 큼
  - 앞선 URL 파손 이슈(`user:@password@host`) 수정 후, 연결은 되지만 대상 DB catalog가 없음
- Action taken:
  - `DATABASE_URL` URL 포맷 정상화 완료 (`user:password@host` 형태)
  - 해당 오류를 본 리포트에 추가 기록
- Next action (required):
  1. 운영 PostgreSQL에서 실제 DB 목록 확인
  2. `DATABASE_URL` DB 이름을 실존 catalog로 정정하거나, `minisaas_db` 생성
  3. Cloud Run revision 롤링 후 `/auth/login/mobile` 재검증

### 6) Alembic baseline 충돌 (`DuplicateTableError`)
- Symptom:
  - `alembic upgrade head` 실행 중 baseline 단계에서 실패
  - error: `relation "ix_board_posts_author_id" already exists`
- Meaning:
  - DB에는 이미 일부 테이블/인덱스가 존재하는데 `alembic_version` 정합이 맞지 않는 상태
  - 즉, "빈 DB 최초 마이그레이션" 조건이 깨진 상태에서 baseline 재적용 충돌
- Safe recovery strategy:
  1. `alembic_version` 존재/값 조회
  2. 스키마가 이미 baseline 이상이라면 `alembic stamp <revision>`로 정렬
  3. 이후 `alembic upgrade head` 재실행
- Note:
  - 충돌 객체(`ix_board_posts_author_id`)를 즉시 DROP하는 방식은 데이터/스키마 맥락 확인 전 금지
  - 우선 stamp 기반 정렬이 기본 원칙

### 7) Migration 멱등성 보강 패치 (MyImcoming 패턴 정렬)
- Background:
  - 운영/개발 DB 상태가 완전히 동일하지 않은 상황에서 `alembic upgrade head` 재실행 시 중복 생성 오류가 반복됨
- Applied pattern:
  1. 도메인 테이블 생성 migration에 대표 테이블 존재 체크 후 early return
  2. 컬럼 추가 migration을 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` 형태로 변경
  3. 데이터 백필 migration을 재실행 가능한 SQL 기반으로 단순화
  4. 모델에서 중복 인덱스 선언(`index=True` + 명시적 `Index`) 제거
- Scope:
  - `alembic/versions/20260215_0002` ~ `20260304_0009`
  - `app/domain/{board,blog,chat,push}/models/*` 일부
- Expected effect:
  - 최초/재배포/부분 선반영 상태에서 migration 충돌 확률 감소
  - 동일 migration 재실행 시 실패 대신 no-op에 가깝게 동작

## Code Changes
- Commit `8141026`
  - Structured auth failure logs 추가
  - files:
    - `app/core/exceptions.py`
    - `app/core/auth/strategies/mobile_strategy.py`

- Commit `3ed9ed9`
  - Redis 예외 시 auth 500 방지
  - file:
    - `app/core/auth/jwt_manager.py`

## Cloud Run Revisions
- `min-minisaas-backend-00019-6zk` (API secret fix 반영)
- `min-minisaas-backend-00021-p8p` (Firebase project id fix 반영)
- `min-minisaas-backend-00023-vss` (Redis TLS URL 반영)

## Verification Checklist
- [x] `API_SECRET_KEY` secret trailing newline 제거
- [x] `FIREBASE_PROJECT_ID` secret trailing newline 제거
- [x] `REDIS_URL` 스킴 `rediss://` 적용
- [x] Cloud Run latest revision 100% traffic 확인
- [x] Auth 실패 원인 로그 서버에 구조화 출력 확인
- [x] Redis 예외 fail-open 패치 반영
- [x] Redis TLS(`rediss://`) 운영 반영
- [ ] 멱등성 보강 패치 회귀 테스트(단위/통합) 완료
- [ ] 멱등성 보강 패치 커밋/배포 여부 최종 승인

## Preventive Actions (Must Keep)
1. Secret 등록 시 newline 차단
   - 반드시 `printf %s 'value' | gcloud secrets versions add ... --data-file=-` 사용
   - `echo` 사용 금지(기본 newline 포함)
2. Secret health check 자동화
   - 배포 전: critical secrets raw-byte 검사(`0a` 여부)
   - 배포 후: smoke API check(`/auth/me`, `/auth/login/mobile`)
3. Redis resilience
   - 현재: fail-open으로 500 방지
   - 추후: reconnect/backoff, circuit-breaker, degraded-mode metric 추가
4. 운영 가시성
   - AuthException 로그 유지
   - `error_code`, `platform`, `has_auth`, `reason` 기준 알림 룰 추가
5. TLS policy
   - 운영 Redis URL 스킴은 `rediss://`만 허용하도록 CI 검증 추가
6. DB URL catalog validation
   - 배포 전 `DATABASE_URL`의 DB 이름 존재 여부를 preflight check로 검증
   - 없으면 배포 차단
7. Migration idempotency policy
   - 신규 migration은 가능한 범위에서 재실행 안전(idempotent)하게 작성
   - `create_all` 기반 baseline과 후속 domain migration의 책임 경계 명확화
   - CI에서 빈 DB/부분 구성 DB 2가지 시나리오로 `alembic upgrade head` 검증

## Related App-side Work (same session)
- Firebase 설정 재정렬(`flutterfire configure`)
- 앱 버전 상향: `1.0.5+4`
- 배포 아티팩트 생성:
  - AAB, IPA 빌드 완료
