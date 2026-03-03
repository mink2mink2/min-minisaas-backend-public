# AI/31 — RDIV 실행 런북 (Execution Runbook)

> AI 작업 시작 시 이 런북을 기준으로 문서 + 코드 + 검증까지 완료한다.
> **기본 지시문**: `README.md를 먼저 읽고, README에 적힌 Start Here/Default Instruction대로 /docs/AI/31_rdiv_execution_runbook.md 기준으로 문서+코드+검증까지 완료해.`

---

## 0. 작업 시작 전 필독

1. `docs/README.md` → DoD, Architecture Rules 확인
2. `docs/AI/20_tasks_queue.md` → 현재 태스크 우선순위 확인
3. `docs/AI/30_context_pack.md` → 프로젝트 상태 및 패턴 확인

---

## 1. R — 요구사항 확인 (Requirements)

작업 전 반드시 확인:

```
docs/R/00_overview.md          # 프로젝트 범위/목적
docs/R/10_user_stories.md      # 관련 유저 스토리 확인
docs/R/20_acceptance_criteria.md  # 인수 조건 확인
docs/R/40_traceability.md      # 기존 API↔테스트 연결 확인
```

**변경 발생 시**: 새 요구사항이면 `R/10_user_stories.md`에 추가.

---

## 2. D — 설계 확인 및 갱신 (Design)

### 아키텍처 레이어 확인 (필수)

`docs/D/10_architecture.md`의 레이어 구조 반드시 확인:

| 레이어 | 위치 | 금지 사항 |
|--------|------|---------|
| HTTP 계약 | `api/v1/endpoints/` | 비즈니스 로직 직접 작성 금지 |
| 비즈니스 로직 | `domain/*/services.py` | HTTP 코드 (Request/Response) 직접 사용 금지 |
| 인프라 | `core/` | 도메인 비즈니스 로직 포함 금지 |
| 횡단 관심사 | `middleware/` | 도메인 종속 로직 포함 금지 |

### API 변경 시

```
docs/D/30_api_contract.md 갱신 필수
docs/D/90_decisions.md에 변경 이유 기록 (파괴적 변경의 경우)
docs/R/40_traceability.md 매트릭스 갱신
```

### DB 스키마 변경 시

```
1. alembic revision --autogenerate -m "변경 설명"
2. 마이그레이션 파일 검토 (autogenerate 오류 가능성)
3. docs/D/20_data_model.md 갱신
```

---

## 3. I — 구현 (Implementation)

### 새 기능 추가 체크리스트

```
[ ] 어느 레이어/도메인에 속하는지 판단
[ ] domain/{feature}/ 아래 독립 파일로 생성
    - models.py: ORM 모델
    - schemas.py: Pydantic 스키마
    - services.py: 비즈니스 로직
    - handlers.py: EventBus 핸들러 (필요시)
[ ] api/v1/endpoints/{domain}.py에 라우터 추가
[ ] Depends()로 의존성 주입 (직접 객체 생성 금지)
[ ] Rate Limiting 적용 여부 검토 (공개 엔드포인트)
[ ] 이벤트 발행 추가 (다른 도메인에 알림 필요한 경우)
[ ] docs/I/20_change_log.md 갱신
```

### 코딩 규칙 (AI/10_coding_rules.md 참고)

```python
# ✅ 올바른 패턴
@router.post("/posts")
async def create_post(
    data: PostCreate,
    service: BoardService = Depends(get_board_service),  # 의존성 주입
    user: User = Depends(get_current_user),
):
    return await service.create_post(user.id, data)

# ❌ 잘못된 패턴 (라우터에 비즈니스 로직 작성)
@router.post("/posts")
async def create_post(data: PostCreate, db: AsyncSession = Depends(get_db)):
    post = BoardPost(**data.dict())  # ❌ 비즈니스 로직을 라우터에 작성
    db.add(post)
    await db.commit()
    return post
```

---

## 4. V — 검증 (Verification)

### 보안 체크 (코드 변경 시 필수)

`docs/V/30_security_review.md` 체크리스트 확인:

```
[ ] 새 공개 엔드포인트에 Rate Limiting 적용됨
[ ] 민감정보 로그 출력 없음 (토큰, DB URL 등)
[ ] SQL Injection 방지 (ORM 사용, raw query 최소화)
[ ] JWT 검증 우회 경로 없음
[ ] Production에서 /docs, /redoc 비활성화 유지
```

### 테스트 작성 및 실행

```bash
# 1. 새 기능에 대한 테스트 작성
# tests/unit/domain/{feature}/test_{feature}_service.py
# tests/api/test_{feature}_endpoints.py

# 2. 테스트 실행
pytest tests/ -v

# 3. 결과 기록
# docs/V/20_test_cases.md에 새 테스트 케이스 추가
```

**규칙**: 테스트 없이 완료 처리 금지.

---

## 5. 문서 동시 갱신 (DoD)

작업 완료 전 반드시 갱신:

```
[ ] R/40_traceability.md — API 추가/변경 시
[ ] D/30_api_contract.md — API 계약 변경 시
[ ] D/20_data_model.md — DB 스키마 변경 시
[ ] D/90_decisions.md — 아키텍처 결정 변경 시
[ ] I/10_implementation_plan.md — 태스크 완료 시
[ ] I/20_change_log.md — 모든 변경 시
[ ] V/20_test_cases.md — 테스트 추가 시
[ ] AI/20_tasks_queue.md — 태스크 상태 변경 시
```

---

## 6. DoD 최종 체크

```
[ ] 모든 테스트 통과 (pytest 결과 확인)
[ ] V/30_security_review.md 체크리스트 통과
[ ] R/D/I/V 문서 동시 갱신 완료
[ ] API 계약 변경 시 앱 팀에 전달 (D/30_api_contract.md)
[ ] change_log.md 갱신 완료
```

---

## 빠른 참조 명령어

```bash
# 서버 실행
uvicorn app.main:app --reload --port 8000

# 테스트 전체
pytest tests/ -v

# 마이그레이션
alembic upgrade head

# 보안 검사
bash scripts/verify_no_secrets.sh

# 린터
ruff check app/
black --check app/
```
