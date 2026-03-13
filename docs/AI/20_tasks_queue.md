# AI/20 — 작업 큐

새 작업은 여기에 추가. 완료 시 ✅ 표시 후 `I/20_change_log.md`에 기록.

---

## 대기 중

| 우선순위 | 작업 | 관련 문서 |
|---------|------|---------|
| 높음 | CORS 설정 환경변수 기반으로 수정 (C1) | D/10, V/30 |
| 높음 | bare except 제거 → 구체적 예외 타입 적용 (C2) | V/30 |
| 높음 | N+1 쿼리 수정 (board posts selectinload 적용) (C3) | D/20 |
| 높음 | CSRF 검증 `hmac.compare_digest()` 적용 (C4) | V/30 |
| 높음 | Board 카테고리 관리 admin 권한 체크 구현 (C5) | D/30, V/30 |
| 높음 | FCM 토큰 검증 구현 (C6) | V/30 |
| 높음 | 통합 테스트 Phase 3~7 완료 (현재 41/143) | V/10 |
| 중 | Refresh Token 구현 (현재 24시간 만료 후 재로그인) | D/30 |
| 중 | 토큰 블랙리스트 구현 (로그아웃 후 즉시 무효화) | V/30 |
| 중 | user.profile_updated 이벤트 발행 구현 (P0) | D/10 |
| 중 | blog.post.updated/deleted 이벤트 구현 (P1) | D/10 |
| 중 | DB Connection Pooling 설정 (H2) | D/10 |
| 중 | GCP Cloud Run 배포 | I/30 |
| 낮음 | WebSocket 멀티 인스턴스 지원 (Redis Pub/Sub) | D/10 |
| 낮음 | Structured JSON 로깅 | I/30 |
| 낮음 | Points API 엔드포인트 추가 | D/30 |
| 낮음 | PDF API 엔드포인트 완성 | D/30 |
| 낮음 | blog.author.subscribed/unsubscribed 이벤트 (P2) | D/10 |

## 완료됨

| 날짜 | 작업 |
|------|------|
| 2026-03-13 | docs/AI/ 문서 체계 구축 |
| 2026-03-06 | Coin simulator API (Task 8A) |
| 2026-03-04 | 이벤트 드리븐 아키텍처 검증 (Task 7) |
| 2026-03-01 | Push 백엔드 구현 완료 (Task 6) |
| 2026-02-22 | Blog 백엔드 구현 완료 (Task 5) |
| 2026-02-18 | Board 백엔드 구현 완료 (Task 4) |
| 2026-02-15 | CSRF 토큰 보호 구현 (Task 5 보안) |
| 2026-02-15 | Core/Domain 레이어 분리 리팩토링 (Task 8) |
| 2026-02-15 | Chat 백엔드 + WebSocket 구현 완료 (Task 2) |
| 2026-02-11 | Auth 보안 P1~P5 완료 (76/76 테스트 통과) |
| 2026-02-01 | 프로젝트 기획 및 설계 (Task 1) |
