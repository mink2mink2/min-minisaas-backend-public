# Incident: Blog Schema Mismatch (2026-02-16)

## Summary
- 증상: `GET /api/v1/blog/categories`가 `500 Internal Server Error` 반환
- 사용자 영향: 앱 블로그 에디터에서 `카테고리 로딩 실패` 발생

## Root Cause
- Alembic `20260216_0005_blog_domain.py`가 `blog_categories`에 `is_deleted`를 생성하지 않음
- SQLAlchemy `BlogCategory` 모델은 `BaseModel` 상속으로 `is_deleted`를 항상 기대함
- 결과적으로 쿼리 시 `column blog_categories.is_deleted does not exist` 예외 발생

## Follow-up Incidents (same day)
- `POST /api/v1/blog/posts`에서 `500` 발생
  - 원인: endpoint 선언 `response_model=dict` vs 실제 반환 `BlogPostResponse` 타입 불일치
  - 조치: `GET/POST/PUT /blog/posts*`의 `response_model`을 `BlogPostResponse`로 정합화
- 발행 성공(201)인데 목록(`feed`)에 글이 보이지 않음
  - 원인: `BlogService.create_post()`에서 `commit()` 누락으로 트랜잭션 롤백
  - 조치: `await self.db.commit()` 추가
- 블로그 카테고리 선택지 없음
  - 원인: blog category 기본 시드 부재
  - 조치: `scripts/seed_blog_categories.py` 추가 및 `make setup`에 연결

## What Was Executed
1. `alembic upgrade head` 실행 (기존 revision 적용 확인)
2. 누락 보정 migration 추가
   - `alembic/versions/20260216_0007_blog_basemodel_columns.py`
   - 대상: `blog_categories.is_deleted`, `blog_likes.updated_at/is_deleted`, `blog_subscriptions.updated_at/is_deleted`
3. 스키마 가드 추가
   - `scripts/verify_schema.py`
   - `make verify`에 스키마 검증 포함

## Prevention
- 배포 전/후 `make verify`를 필수 게이트로 사용
- 스키마 누락은 `verify_schema.py`에서 즉시 실패 처리
- 실패 시 앱 오픈 금지, migration 적용 후 재검증

## Operator Runbook
```bash
make migrate
make verify
```

`make verify` 실패 시:
1. 실패 메시지에서 누락 테이블/컬럼 확인
2. migration 작성/적용
3. `make verify` 재실행 후 success 확인
