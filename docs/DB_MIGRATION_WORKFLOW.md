# DB Migration Workflow

## 목적
이 문서는 `min-minisaas-backend`의 데이터베이스 변경을 안전하게 배포하기 위한 표준 절차를 정의합니다.

## 원칙
- 스키마 변경은 반드시 Alembic migration으로 관리합니다.
- 운영 경로에서 `Base.metadata.create_all()`을 직접 호출하지 않습니다.
- 최초 설치와 업데이트를 분리합니다.
  - 최초 설치: `bootstrap + migrate + seed-categories + verify`
  - 업데이트: `migrate + seed-categories + seed-blog-categories + verify`
- `verify`는 연결성뿐 아니라 필수 테이블/컬럼 스키마 가드와 기본 카테고리 seed 가드까지 통과해야 성공으로 봅니다.

## 명령 요약
```bash
# 최초 설치
make setup

# 개별 실행
make bootstrap   # DB 없으면 생성
make migrate     # alembic upgrade head
make seed-categories  # board 기본 카테고리 멱등 시드
make seed-blog-categories  # blog 기본 카테고리 멱등 시드
make verify      # postgres/redis + 필수 스키마 점검
make verify-schema  # 필수 스키마 점검 단독 실행
make release-prepare  # 운영 업데이트용(bootstrap 없이 migrate+seed+verify)
```

## 신규 스키마 변경 절차
1. SQLAlchemy 모델 수정
2. 마이그레이션 생성
```bash
.venv/bin/alembic revision --autogenerate -m "describe change"
```
3. 생성된 revision 검토 (nullable/default/index/drop 안전성 확인)
4. 로컬 적용
```bash
make migrate
```
5. 런타임 검증
```bash
make verify
.venv/bin/pytest -q tests/test_runtime_connectivity.py
```
6. 필요 시 downgrade 검증
```bash
.venv/bin/alembic downgrade -1
.venv/bin/alembic upgrade head
```

## 배포 순서
1. 앱 배포 전 DB migration 먼저 적용 (`make migrate`)
2. migration 성공 후 seed 적용 (`make seed-categories && make seed-blog-categories`)
3. `make verify` 통과 확인
4. 검증 통과 후 앱 버전 배포

## 롤백 원칙
- 긴급 이슈 시 앱 기능 플래그로 우선 차단
- DB 롤백이 필요한 경우에만 `alembic downgrade` 수행
- 파괴적 변경(drop/rename)은 expand-contract 전략으로 2회 배포로 처리

## Expand-Contract 규칙
- Expand: 컬럼/테이블 추가, 구버전과 호환
- Migrate: 앱이 신구 스키마 모두 읽고 쓰도록 과도기 운영
- Contract: 구 컬럼 제거

## 운영 체크리스트
- `.env`의 `DATABASE_URL`, `REDIS_URL`, `REDIS_PASSWORD` 확인
- migration 파일 리뷰 완료
- 백업/스냅샷 전략 확인
- 배포 후 `tests/test_runtime_connectivity.py` 통과 확인

## Fail to Success 운영 규칙
- `make verify` 또는 `make verify-schema`가 실패하면 앱 배포/재시작을 진행하지 않습니다.
- 담당자는 실패 메시지의 테이블/컬럼 누락 원인에 맞는 migration을 적용합니다.
  - 기본 조치: `.venv/bin/alembic upgrade head`
  - migration 누락이면 새 revision 추가 후 재적용
- seed 누락 실패 시 기본 조치:
  - `.venv/bin/python scripts/seed_board_categories.py`
  - `.venv/bin/python scripts/seed_blog_categories.py`
- 조치 후 `make verify`를 재실행해 success를 확인한 뒤에만 서비스 오픈합니다.
