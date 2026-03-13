# AI/31 — RDIV 실행 Runbook

> 모든 작업은 이 순서를 따른다. 예외 없음.

---

## Step 0: 컨텍스트 로드

작업 시작 전 반드시 아래 순서로 읽는다:

1. `docs/README.md` — 전체 규칙, DoD, Architecture Rules
2. `docs/AI/00_project_brief.md` — 프로젝트 현황 (도메인 구성, 기술 부채)
3. `docs/AI/10_coding_rules.md` — 코딩 규칙 (DDD, EventBus, async SQLAlchemy)
4. `docs/AI/20_tasks_queue.md` — 현재 작업 확인
5. 작업 관련 `D/` 문서 — API 계약, 데이터 모델, 이벤트 목록

---

## Step 1: R (Requirements 확인)

- 작업이 기존 유저 스토리(`R/10_user_stories.md`)에 해당하는가?
- 새 요구사항이면 `R/10_user_stories.md`에 추가
- 새 도메인 기능이면 `R/20_feature_spec.md`에 스펙 먼저 정의

---

## Step 2: D (Design 갱신 — 코드 작성 전)

코드보다 문서를 먼저 갱신한다.

- REST API 변경 → `D/30_api_contract.md` 먼저 갱신
- DB 모델 변경 → `D/20_data_model.md` 먼저 갱신
- 새 이벤트 추가 → `D/10_architecture.md` 이벤트 목록 갱신
- 아키텍처 결정 → `D/90_decisions.md`에 ADR 추가

---

## Step 3: I (Implementation)

### 3.1 코드 작성 체크리스트

- [ ] `docs/AI/10_coding_rules.md` 규칙 준수
- [ ] API 레이어에 비즈니스 로직 없음 (Service 위임만)
- [ ] Domain 간 직접 import 없음 (EventBus 사용)
- [ ] 모든 DB 쿼리는 `AsyncSession` 비동기 패턴
- [ ] N+1 쿼리 방지 (`selectinload` 적용 확인)
- [ ] 환경변수 하드코딩 없음 (`app/core/config.py` 사용)
- [ ] 새 엔드포인트에 `Depends(get_current_user)` 인증 적용
- [ ] 민감 정보 로그 출력 없음
- [ ] bare except 없음

### 3.2 새 도메인 추가 시 체크리스트

```
app/domain/{feature}/
├── models.py     ← 1. ORM 모델 먼저
├── schemas.py    ← 2. Pydantic 스키마
├── services.py   ← 3. 비즈니스 로직
└── handlers.py   ← 4. EventBus 핸들러 (필요 시)
```

- `app/api/v1/endpoints/{feature}.py` — 엔드포인트 추가
- `app/api/v1/router.py` — 라우터 등록
- `app/main.py` — startup()에 핸들러 등록
- Alembic 마이그레이션 생성 및 검토

### 3.3 Alembic 마이그레이션

```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "add_{feature}_tables"

# 생성된 마이그레이션 파일 반드시 검토 후 적용
alembic upgrade head
```

### 3.4 빌드 확인

```bash
cd /path/to/min-minisaas-backend

# 코드 품질 검사 (모두 통과 필수)
make check    # black, isort, flake8, pylint

# 전체 테스트
pytest tests/ -v

# Docker 빌드
docker compose up -d --build
```

빌드 또는 테스트 실패 시 → 수정 후 재확인. 완료 전까지 다음 단계 진행 금지.

### 3.5 구현 현황 갱신

- `I/10_implementation_plan.md` 해당 항목 체크
- `I/20_change_log.md` 변경 내용 기록

---

## Step 4: V (Verification)

### 4.1 보안 체크

`V/30_security_review.md` 관련 항목 확인:
- 새 엔드포인트에 JWT 인증이 적용됐는가?
- 민감 정보가 로그에 출력되지 않는가?
- Rate Limiting이 민감한 엔드포인트에 적용됐는가?
- 환경변수 외부 노출이 없는가?

### 4.2 기능 테스트

```bash
# 전체 테스트
pytest tests/ -v

# 특정 도메인 테스트
pytest tests/test_board_endpoints.py -v
pytest tests/test_auth_endpoints.py -v
pytest tests/test_chat_endpoints.py -v

# 헬스체크
curl http://localhost:8000/health
```

### 4.3 EventBus 이벤트 흐름 확인

새 이벤트 추가 시:
```bash
# 이벤트 발행 확인 (로그에서)
# 예: board.post.created 발행 → push 핸들러 수신 확인
pytest tests/test_event_handlers.py -v
```

---

## Step 5: 완료 처리

- [ ] `AI/20_tasks_queue.md`에서 작업 ✅ 표시
- [ ] DoD 체크리스트 모두 통과 확인 (`docs/README.md` 참고)

---

## 금지 사항

- 문서 갱신 없이 코드만 변경하는 것
- API 레이어에 비즈니스 로직 직접 작성
- Domain 간 직접 import (EventBus 사용)
- 동기 SQLAlchemy 쿼리 (`db.query()` 사용 금지)
- 환경변수 코드 하드코딩
- `except:` bare except 사용
- 인증 필요 엔드포인트에 `Depends(get_current_user)` 누락
- `make check` 실패 상태로 완료 처리
- 테스트 없이 새 기능 완료 처리
- Docker 빌드 확인 없이 완료 처리
- Alembic 마이그레이션 검토 없이 그대로 적용
