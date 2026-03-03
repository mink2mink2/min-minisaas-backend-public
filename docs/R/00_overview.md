# R/00 — 프로젝트 개요

## 프로젝트 정보

| 항목 | 내용 |
|------|------|
| 프로젝트명 | MiniSaaS Backend API Server |
| 버전 | v1.0 (Production 준비 중) |
| 담당 팀 | min-minisaas 개발팀 |
| 최종 갱신 | 2026-03-03 |

---

## 프로젝트 목적

MiniSaaS 백엔드는 **Flutter 모바일 앱(Min MiniSaaS)을 위한 REST API 서버**이다.

채팅, 게시판, 블로그, 푸시 알림, 인증, 포인트 기능을 제공하며, 소규모 SaaS 서비스의 공통 백엔드 인프라를 빠르게 구축하기 위한 레퍼런스 구현이다.

### 핵심 가치
- **빠른 개발**: 공통 SaaS 기능을 미리 구현하여 재사용 가능
- **확장성**: 도메인 추가/제거가 기존 도메인에 영향을 주지 않는 구조
- **유지보수성**: DDD + Event-driven 아키텍처로 레이어 간 명확한 역할 분리
- **보안**: OAuth 서버사이드 검증, JWT 인증, Rate Limiting 내장

---

## 범위

### 포함된 도메인

| 도메인 | 설명 | 상태 |
|--------|------|------|
| **auth** | Google/Kakao/Naver OAuth 로그인, JWT 발급/갱신/만료 | ✅ 완료 |
| **chat** | 1:1 실시간 채팅방, WebSocket 메시지, 메시지 이력 조회 | ✅ 완료 |
| **board** | 커뮤니티 게시판 CRUD, 댓글, 좋아요, 북마크, 검색 | ✅ 완료 |
| **blog** | 블로그 게시글 CRUD, 구독, 피드, 좋아요 | ✅ 완료 |
| **push** | FCM 토큰 등록/관리, 알림 목록, 읽음 처리, 알림 발송 | ✅ 완료 |
| **points** | 사용자 포인트 적립/사용 (기반 구조) | 🔄 기반 구현 |

### 포함되지 않는 범위
- 결제 처리 (Payment Gateway 연동)
- 파일 업로드/스토리지 (S3, GCS 연동)
- 관리자 대시보드 UI
- 분석/리포팅 기능

---

## 사용자 역할

### 일반 사용자 (Authenticated User)
OAuth(Google, Kakao, Naver)로 로그인한 앱 사용자.
- 채팅방 생성 및 참여
- 게시글/블로그 작성, 수정, 삭제
- 댓글, 좋아요, 북마크 기능 사용
- 블로그 구독
- 푸시 알림 수신

### 관리자 (Admin)
시스템 관리 권한을 가진 사용자.
- 모든 게시글/댓글 삭제
- 사용자 관리
- 푸시 알림 수동 발송
- 포인트 지급/회수

### 비인증 사용자 (Anonymous)
- 공개 게시글 목록/상세 조회 (읽기 전용, Rate Limiting 적용)
- 블로그 공개 포스트 조회

---

## 핵심 제약사항

### 성능 제약
| 지표 | 목표값 | 비고 |
|------|--------|------|
| 일간 활성 사용자 (DAU) | 10,000명 | 피크 타임 집중 가정 |
| 평균 응답시간 | < 100ms | DB 쿼리 포함 |
| 95th percentile 응답시간 | < 500ms | |
| 99th percentile 응답시간 | < 1,000ms | |
| 동시 접속자 | 1,000+ | WebSocket 포함 |

### 보안 제약
- **JWT 인증 필수**: 공개 엔드포인트를 제외한 모든 API에 Bearer 토큰 인증 적용
- **OAuth 서버사이드 검증**: 클라이언트 토큰을 서버에서 OAuth 제공자에 재검증
- **Rate Limiting**: 공개 엔드포인트 기본 60 req/min, 게시글 10개/분, 댓글 1개/초
- **HTTPS 전용**: HTTP 요청 리다이렉트 또는 거부

### 기술 제약
- **Python 3.11+**: 최신 async/await 패턴 사용
- **FastAPI 0.100+**: 비동기 엔드포인트 기본
- **PostgreSQL 15+**: 주 데이터 저장소
- **Redis 7+**: 캐싱 및 EventBus 백엔드
- **Alembic**: 데이터베이스 스키마 마이그레이션 도구 (수동 SQL 마이그레이션 금지)

### 운영 제약
- **가용성**: 99.9% uptime (월 최대 43분 다운타임 허용)
- **배포 방식**: Docker 컨테이너 기반, GCP Cloud Run 또는 GKE
- **환경 분리**: development / staging / production 환경 분리 필수
- **비밀값 관리**: 환경변수 또는 Secret Manager를 통해 관리 (코드에 하드코딩 금지)

---

## 외부 시스템 의존성

| 시스템 | 용도 | 비고 |
|--------|------|------|
| Google Firebase Auth | Google OAuth JWT 검증 | Firebase Admin SDK |
| Google FCM | 푸시 알림 발송 | Firebase Admin SDK |
| Kakao OAuth | 카카오 소셜 로그인 | 카카오 API 서버 검증 |
| Naver OAuth | 네이버 소셜 로그인 | 네이버 API 서버 검증 |
| PostgreSQL | 주 데이터베이스 | GCP Cloud SQL 또는 직접 설치 |
| Redis | 캐시 / 이벤트 버스 | GCP Memorystore 또는 직접 설치 |

---

## 관련 문서

- [R/10_user_stories.md](10_user_stories.md) — 상세 유저 스토리
- [R/20_acceptance_criteria.md](20_acceptance_criteria.md) — 인수 기준
- [R/30_nonfunctional.md](30_nonfunctional.md) — 비기능 요구사항 상세
- [D/10_architecture.md](../D/10_architecture.md) — 시스템 아키텍처
