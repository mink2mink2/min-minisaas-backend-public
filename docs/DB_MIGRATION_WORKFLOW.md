# DB Migration Workflow

## 목적
이 문서는 `min-minisaas-backend`의 데이터베이스 변경을 안전하게 배포하기 위한 표준 절차를 정의합니다.

## 원칙
- 스키마 변경은 반드시 Alembic migration으로 관리합니다.
- 운영 경로에서 `Base.metadata.create_all()`을 직접 호출하지 않습니다.
- 최초 설치와 업데이트를 분리합니다.
  - 최초 설치: `bootstrap + migrate + verify`
  - 업데이트: `migrate + verify`

## 명령 요약
```bash
# 최초 설치
make setup

# 개별 실행
make bootstrap   # DB 없으면 생성
make migrate     # alembic upgrade head
make verify      # postgres/redis 연결 점검
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
2. migration 성공 후 앱 버전 배포
3. 배포 직후 `make verify`로 의존성 상태 확인

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
