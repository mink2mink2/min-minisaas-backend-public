# I/10 — 구현 계획 및 현황

> 최종 갱신: 2026-03-03

---

## 전체 진행 현황

| 태스크 | 설명 | 코드 규모 | 상태 | 완료일 |
|--------|------|---------|------|--------|
| Task 1 | 프로젝트 기획 및 설계 | — | ✅ 완료 | 2026-02-01 |
| Task 2 | Chat 백엔드 구현 | ~500 lines | ✅ 완료 | 2026-02-11 |
| Task 3 | Chat Flutter 앱 | ~600 lines | ✅ 완료 | 2026-02-13 |
| Task 4 | Board 백엔드 구현 | ~800 lines | ✅ 완료 | 2026-02-18 |
| Task 5 | Blog 백엔드 구현 | ~1,000 lines | ✅ 완료 | 2026-02-22 |
| Task 6 | Push 백엔드 구현 | ~1,195 lines | ✅ 완료 | 2026-03-01 |
| Task 7 | 통합 테스트 | 143 테스트 계획 | 🔄 진행 중 (41/143) | 2026-03-15 목표 |
| Task 8 | 배포 | GCP 배포 | ⏳ 대기 | 2026-03-20 목표 |

**전체 진행률**: 75% (핵심 기능 구현 완료, 테스트/배포 진행 중)

---

## Task 1: 프로젝트 기획 및 설계 ✅

**기간**: 2026-02-01

### 완료 항목
- [x] 도메인 정의 (auth, chat, board, blog, push, points)
- [x] DDD 아키텍처 설계
- [x] DB 스키마 설계
- [x] API 엔드포인트 목록 작성
- [x] 기술 스택 결정 (FastAPI, PostgreSQL, Redis, Firebase)

---

## Task 2: Chat 백엔드 구현 ✅

**기간**: 2026-02-05 ~ 2026-02-11
**코드 규모**: ~500 lines

### 완료 항목
- [x] `domain/auth/` — User 모델, 소셜 로그인 서비스, JWT 발급
- [x] `core/auth/google.py` — Firebase ID Token 검증
- [x] `core/auth/kakao.py` — 카카오 API 서버사이드 검증
- [x] `core/auth/naver.py` — 네이버 API 서버사이드 검증
- [x] `domain/chat/` — ChatRoom, ChatMessage 모델, 채팅 서비스
- [x] `api/v1/endpoints/auth.py` — 로그인/로그아웃/내 정보 API
- [x] `api/v1/endpoints/chat.py` — 채팅방/메시지 API + WebSocket
- [x] `middleware/auth.py` — JWT 인증 미들웨어
- [x] Alembic 마이그레이션 — users, chat_rooms, chat_participants, chat_messages

---

## Task 3: Chat Flutter 앱 ✅

**기간**: 2026-02-11 ~ 2026-02-13
**코드 규모**: ~600 lines

### 완료 항목
- [x] 소셜 로그인 화면 (Google, Kakao, Naver)
- [x] 채팅방 목록 화면
- [x] 실시간 채팅 화면 (WebSocket)
- [x] JWT 토큰 보안 저장소 연동

---

## Task 4: Board 백엔드 구현 ✅

**기간**: 2026-02-14 ~ 2026-02-18
**코드 규모**: ~800 lines

### 완료 항목
- [x] `domain/board/` — BoardPost, BoardComment, BoardReaction 모델
- [x] `domain/board/services.py` — CRUD, 좋아요, 북마크, 검색
- [x] `domain/board/handlers.py` — 게시글 생성 이벤트 발행
- [x] `api/v1/endpoints/board.py` — 전체 Board API 엔드포인트
- [x] Rate Limiting — 게시글 10개/분, 댓글 1개/초
- [x] Alembic 마이그레이션 — board_posts, board_comments, board_reactions

---

## Task 5: Blog 백엔드 구현 ✅

**기간**: 2026-02-19 ~ 2026-02-22
**코드 규모**: ~1,000 lines

### 완료 항목
- [x] `domain/blog/` — BlogPost, BlogLike, BlogSubscription 모델
- [x] `domain/blog/services.py` — CRUD, 좋아요, 구독, 피드 생성
- [x] `domain/blog/handlers.py` — 블로그 글 발행 이벤트 발행
- [x] `api/v1/endpoints/blog.py` — 전체 Blog API 엔드포인트
- [x] Slug 자동 생성 로직 (`title` → `url-friendly-slug`)
- [x] Alembic 마이그레이션 — blog_posts, blog_likes, blog_subscriptions

---

## Task 6: Push 백엔드 구현 ✅

**기간**: 2026-02-23 ~ 2026-03-01
**코드 규모**: ~1,195 lines

### 완료 항목
- [x] `core/fcm.py` — Firebase Admin SDK 초기화
- [x] `domain/push/` — FCMToken, PushNotification 모델
- [x] `domain/push/services.py` — 토큰 CRUD, 알림 목록/읽음/삭제
- [x] `domain/push/fcm_service.py` — FCM 실제 발송 로직
- [x] `domain/push/handlers.py` — EventBus 구독
  - `board.post.created` → 작성자 팔로워에게 알림
  - `board.comment.created` → 게시글 작성자에게 알림
  - `blog.post.created` → 구독자에게 알림
  - `chat.message.received` → 오프라인 사용자에게 알림
- [x] `api/v1/endpoints/push.py` — 전체 Push API 엔드포인트
- [x] Alembic 마이그레이션 — fcm_tokens, push_notifications

---

## Task 7: 통합 테스트 🔄 (진행 중)

**기간**: 2026-03-02 ~ 2026-03-15 (목표)
**진행률**: 41/143 (29%)

### Phase 별 진행 현황

| Phase | 설명 | 계획 | 완료 | 상태 |
|-------|------|------|------|------|
| Phase 1 | Service Unit Tests | 20 | 20 | ✅ 완료 |
| Phase 2 | API Endpoint Tests | 21 | 21 | ✅ 완료 |
| Phase 3 | Event Handler Tests | 10 | 0 | 📋 계획 |
| Phase 4 | FCM Integration Tests | 10 | 0 | 📋 계획 |
| Phase 5 | Cross-Domain Tests | 15 | 0 | 📋 계획 |
| Phase 6 | Performance Tests | 8 | 0 | 📋 계획 |
| Phase 7 | Flutter E2E Tests | 10 | 0 | 📋 계획 |
| **합계** | | **143** | **41** | **29%** |

### 다음 작업
- [ ] Phase 3: EventBus 핸들러 단위 테스트 작성
- [ ] Phase 4: FCM mock을 이용한 통합 테스트
- [ ] Phase 5: 도메인 간 이벤트 흐름 통합 테스트

---

## Task 8: 배포 ⏳ (대기)

**예정**: 2026-03-20

### 계획 항목
- [ ] Docker 이미지 빌드 및 테스트
- [ ] GCP Cloud Run 배포 설정
- [ ] Cloud SQL (PostgreSQL) 연결
- [ ] GCP Memorystore (Redis) 연결
- [ ] Firebase 서비스 계정 키 Secret Manager 등록
- [ ] Alembic 마이그레이션 실행 (Production)
- [ ] 도메인 및 SSL 인증서 설정
- [ ] 헬스체크 및 모니터링 설정

상세 가이드: [I/30_deploy_guide.md](30_deploy_guide.md)

---

## 기술 부채

| 항목 | 중요도 | 설명 |
|------|--------|------|
| Refresh Token 미구현 | 높음 | 현재 24시간 후 재로그인 필요 |
| 토큰 블랙리스트 미구현 | 중간 | 로그아웃 후 토큰 즉시 무효화 불가 |
| WebSocket 멀티 인스턴스 지원 | 중간 | 현재 단일 인스턴스만 동작 |
| chat_messages 파티셔닝 | 낮음 | 대용량 시 성능 대비 (현재 불필요) |
| 이벤트 재시도 메커니즘 | 낮음 | EventBus 실패 시 이벤트 소실 |
| Device Attestation | 낮음 | 앱 무결성 검증 미구현 |
