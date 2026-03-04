# AI/20 — 태스크 큐 (Tasks Queue)

> 현재 진행 중이거나 예정된 작업 목록.
> 작업 시작 전 반드시 이 파일을 읽고 우선순위를 확인한다.

---

## 진행 중 (In Progress)

| ID | 태스크 | 담당 | 브랜치 |
|----|--------|------|--------|
| T7 | Integration Testing Phase 3-7 | AI/개발자 | `feature/integration-tests` |

---

## 대기 중 (Pending)

### P1 — 즉시 처리

| ID | 태스크 | 설명 | 참고 문서 |
|----|--------|------|---------|
| T7-P3 | Event Handler 테스트 (10개) | EventBus 핸들러 단위 테스트 작성 | V/20_test_cases.md |
| T7-P4 | FCM Integration 테스트 (10개) | Firebase mock으로 FCM 발송 테스트 | V/20_test_cases.md |
| T7-P5 | Cross-Domain 테스트 (15개) | 도메인 간 이벤트 전파 E2E 테스트 | V/20_test_cases.md |
| T7-P6 | Performance 테스트 (8개) | 응답시간 <100ms, 동시 요청 500+ | V/30_nonfunctional.md |
| T7-P7 | Flutter E2E 테스트 (10개) | 앱-백엔드 통합 테스트 | V/10_test_plan.md |

### P2 — 배포 전 완료

| ID | 태스크 | 설명 |
|----|--------|------|
| T8-A | GCP 인프라 구성 | Cloud Run, Cloud SQL, Memorystore |
| T8-B | Docker 이미지 빌드/푸시 | Artifact Registry 업로드 |
| T8-C | Alembic 마이그레이션 실행 | Production DB 스키마 적용 |
| T8-D | Firebase 설정 | Service Account, FCM 설정 |
| T8-E | 도메인/SSL 설정 | HTTPS 인증서 |
| T8-F | 모니터링 설정 | Cloud Monitoring, 알림 |

### P1-PDF — PDF Helper 후속 작업

| ID | 태스크 | 설명 | 우선순위 |
|----|--------|------|---------|
| PDF-01 | files.py 비즈니스 로직 분리 | 라우터에 있는 MinIO 업로드/검증 로직을 PDFFileService로 이동 (README 금지 패턴) | 높 |
| PDF-02 | FIREBASE_PROJECT_ID 주입 | .env에 실제 Firebase 프로젝트 ID 설정 (운영 전 필수) | 🔴 긴급 |
| PDF-03 | PDF 이벤트 핸들러 연결 검증 | coroutine warning 재확인 및 이벤트 핸들러 정상 동작 테스트 | 중 |
| PDF-04 | PDF 단위 테스트 작성 | pdf_converter_service, pdf_file_service 테스트 | 중 |

### P3 — 기술 부채

| ID | 태스크 | 설명 | 우선순위 |
|----|--------|------|---------|
| TD-01 | Token refresh 로직 | JWT 만료 시 silent refresh | 중 |
| TD-02 | Refresh token 저장 | Redis 기반 refresh token | 중 |
| TD-03 | Device attestation | Play Integrity / DeviceCheck | 낮 |
| TD-04 | API 버전 전략 | v2 마이그레이션 계획 | 낮 |
| TD-05 | DDoS 방어 | Cloudflare 또는 WAF | 낮 |
| TD-06 | 이미지 업로드 | S3/GCS + CDN | 중 |
| TD-07 | 그룹 채팅 | 다자간 채팅방 | 낮 |

---

## 완료 (Completed)

| ID | 태스크 | 완료일 | 결과 |
|----|--------|--------|------|
| T1 | 프로젝트 기획 | 2026-01-15 | ✅ |
| T2 | Chat Backend 구현 | 2026-02-05 | ✅ ~500줄 |
| T3 | Chat App 구현 | 2026-02-11 | ✅ ~600줄 |
| T4 | Board 구현 | 2026-02-15 | ✅ ~800줄 |
| T5 | Blog 구현 | 2026-02-20 | ✅ ~1,000줄 |
| T6 | Push Backend+App 구현 | 2026-02-28 | ✅ ~2,330줄 |
| T7-P1 | Service Unit Tests (20개) | 2026-02-16 | ✅ 20/20 통과 |
| T7-P2 | API Endpoint Tests (21개) | 2026-02-16 | ✅ 21/21 통과 |

---

## 테스트 진행 현황

```
Phase 1: Service Unit Tests      20/20 ✅ (100%)
Phase 2: API Endpoint Tests      21/21 ✅ (100%)
Phase 3: Event Handler Tests      0/10 📋 (0%)
Phase 4: FCM Integration Tests    0/10 📋 (0%)
Phase 5: Cross-Domain Tests       0/15 📋 (0%)
Phase 6: Performance Tests        0/8  📋 (0%)
Phase 7: Flutter E2E Tests        0/10 📋 (0%)
─────────────────────────────────────────
합계:                            41/143 (29%)
```

---

## 태스크 추가 방법

```markdown
| T새번호 | 태스크 설명 | 구체적 작업 내용 | 관련 문서 |
```

완료 시 `완료` 섹션으로 이동하고 완료일/결과 기재.
