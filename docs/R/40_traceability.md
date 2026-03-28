# R/40 — 추적성 매트릭스 (Traceability Matrix)

> 유저 스토리 → API 엔드포인트 → 테스트 케이스의 추적성을 보장한다.
> API 또는 테스트가 변경될 때 반드시 이 문서도 갱신한다.

---

## AUTH 도메인

| 유저 스토리 | API 엔드포인트 | 테스트 케이스 | 상태 |
|------------|--------------|-------------|------|
| US-A01: Google 로그인 | `POST /api/v1/auth/login/google` | TC-A01-01 ~ TC-A01-06 | ✅ 완료 |
| US-A02: Kakao 로그인 | `POST /api/v1/auth/login/kakao` | TC-A02-01 ~ TC-A02-04 | ✅ 완료 |
| US-A03: Naver 로그인 | `POST /api/v1/auth/login/naver` | TC-A03-01 ~ TC-A03-03 | ✅ 완료 |
| US-A04: 내 정보 조회 | `GET /api/v1/auth/me` | TC-A04-01 ~ TC-A04-03 | ✅ 완료 |
| US-A05: 로그아웃 | `POST /api/v1/auth/logout` | TC-A05-01 ~ TC-A05-02 | ✅ 완료 |

---

## CHAT 도메인

| 유저 스토리 | API 엔드포인트 | 테스트 케이스 | 상태 |
|------------|--------------|-------------|------|
| US-C01: 채팅방 생성 | `POST /api/v1/chat/rooms` | TC-C01-01 ~ TC-C01-04 | ✅ 완료 |
| US-C02: 채팅방 목록 | `GET /api/v1/chat/rooms` | TC-C02-01 ~ TC-C02-03 | ✅ 완료 |
| US-C03: 실시간 메시지 | `WS /api/v1/chat/ws/rooms/{room_id}` | TC-C03-01 ~ TC-C03-05 | 📋 계획 |
| US-C04: 메시지 이력 | `GET /api/v1/chat/rooms/{room_id}/messages` | TC-C04-01 ~ TC-C04-03 | ✅ 완료 |
| US-C05: HTTP 메시지 전송 | `POST /api/v1/chat/rooms/{room_id}/messages` | TC-C05-01 ~ TC-C05-02 | ✅ 완료 |

---

## BOARD 도메인

| 유저 스토리 | API 엔드포인트 | 테스트 케이스 | 상태 |
|------------|--------------|-------------|------|
| US-B01: 게시글 목록 | `GET /api/v1/board/posts` | TC-B01-01 ~ TC-B01-03 | ✅ 완료 |
| US-B02: 게시글 작성 | `POST /api/v1/board/posts` | TC-B02-01 ~ TC-B02-04 | ✅ 완료 |
| US-B03: 게시글 수정 | `PUT /api/v1/board/posts/{id}` | TC-B03-01 ~ TC-B03-03 | ✅ 완료 |
| US-B04: 게시글 삭제 | `DELETE /api/v1/board/posts/{id}` | TC-B04-01 ~ TC-B04-03 | ✅ 완료 |
| US-B05: 좋아요 | `POST/DELETE /api/v1/board/posts/{id}/like` | TC-B05-01 ~ TC-B05-04 | ✅ 완료 |
| US-B06: 북마크 | `POST/DELETE /api/v1/board/posts/{id}/bookmark` | TC-B06-01 ~ TC-B06-02 | 📋 계획 |
| US-B07: 댓글 작성 | `POST /api/v1/board/posts/{id}/comments` | TC-B07-01 ~ TC-B07-03 | ✅ 완료 |
| US-B08: 댓글 목록 | `GET /api/v1/board/posts/{id}/comments` | TC-B08-01 ~ TC-B08-02 | ✅ 완료 |
| US-B09: 댓글 삭제 | `DELETE /api/v1/board/comments/{id}` | TC-B09-01 ~ TC-B09-02 | ✅ 완료 |
| US-B10: 게시글 검색 | `GET /api/v1/board/posts?search={kw}` | TC-B10-01 ~ TC-B10-03 | 📋 계획 |

---

## BLOG 도메인

| 유저 스토리 | API 엔드포인트 | 테스트 케이스 | 상태 |
|------------|--------------|-------------|------|
| US-BL01: 블로그 작성 | `POST /api/v1/blog/posts` | TC-BL01-01 ~ TC-BL01-03 | ✅ 완료 |
| US-BL02: 블로그 수정 | `PUT /api/v1/blog/posts/{id}` | TC-BL02-01 ~ TC-BL02-02 | ✅ 완료 |
| US-BL03: 블로그 삭제 | `DELETE /api/v1/blog/posts/{id}` | TC-BL03-01 ~ TC-BL03-02 | ✅ 완료 |
| US-BL04: 피드 조회 | `GET /api/v1/blog/feed` | TC-BL04-01 ~ TC-BL04-05 | ✅ 완료 |
| US-BL05: 사용자 블로그/상세 조회 | `GET /api/v1/blog/users/{user_id}`, `GET /api/v1/blog/posts/{id}` | TC-BL05-01 ~ TC-BL05-03 | ✅ 완료 |
| US-BL06: 블로그 좋아요 | `POST/DELETE /api/v1/blog/posts/{id}/like` | TC-BL06-01 ~ TC-BL06-03 | ✅ 완료 |
| US-BL07: 블로거 구독 | `POST/DELETE /api/v1/blog/subscribe/{id}` | TC-BL07-01 ~ TC-BL07-04 | 📋 계획 |

---

## PUSH 도메인

| 유저 스토리 | API 엔드포인트 | 테스트 케이스 | 상태 |
|------------|--------------|-------------|------|
| US-P01: FCM 토큰 등록 | `POST /api/v1/push/tokens` | TC-P01-01 ~ TC-P01-03 | ✅ 완료 |
| US-P02: FCM 토큰 갱신 | `PUT /api/v1/push/tokens/{id}` | TC-P02-01 ~ TC-P02-02 | ✅ 완료 |
| US-P03: FCM 토큰 삭제 | `DELETE /api/v1/push/tokens/{token}` | TC-P03-01 ~ TC-P03-02 | ✅ 완료 |
| US-P04: 알림 목록 | `GET /api/v1/push/notifications` | TC-P04-01 ~ TC-P04-03 | ✅ 완료 |
| US-P05: 읽지 않은 수 | `GET /api/v1/push/notifications/unread/count` | TC-P05-01 | ✅ 완료 |
| US-P06: 알림 읽음 | `PUT /api/v1/push/notifications/{id}/read` | TC-P06-01 ~ TC-P06-02 | ✅ 완료 |
| US-P07: 전체 읽음 | `PUT /api/v1/push/notifications/read-all` | TC-P07-01 | ✅ 완료 |
| US-P08: 알림 삭제 | `DELETE /api/v1/push/notifications/{id}` | TC-P08-01 ~ TC-P08-02 | ✅ 완료 |

---

## 진행 현황 요약

| 도메인 | 유저 스토리 수 | 테스트 완료 | 테스트 계획 | 완료율 |
|--------|-------------|-----------|-----------|--------|
| Auth | 5 | 5 | 0 | 100% |
| Chat | 5 | 4 | 1 | 80% |
| Board | 10 | 8 | 2 | 80% |
| Blog | 7 | 5 | 2 | 71% |
| Push | 8 | 5 | 3 | 63% |
| **전체** | **35** | **27** | **8** | **77%** |

---

## Flutter 앱 연동 영향 추적

> API 계약 변경이 앱에 미치는 영향을 추적한다.

| 변경 날짜 | API 변경 내용 | Flutter 영향 | 앱 수정 필요 여부 |
|---------|-------------|------------|----------------|
| 2026-02-15 | Push API 엔드포인트 추가 | FCM 토큰 등록 화면 | ✅ 앱 v1.0에 반영됨 |
| 2026-02-20 | Blog 구독 API 추가 | 블로그 구독 버튼 | ✅ 앱 v1.0에 반영됨 |
| 2026-03-01 | 읽지 않은 알림 수 API | 탭바 뱃지 | ✅ 앱 v1.0에 반영됨 |
| 2026-03-06 | Coin simulator API + `/auth/me.is_superuser` 확장 | `coint simulator` 메뉴와 제어 권한 UI | ✅ 앱 동시 반영 |
| 2026-03-18 | `POST /api/v1/verify/generate-daily/{date_str}` superuser 보호 추가 | 일반 앱 흐름 영향 없음, 운영/관리자 호출만 stricter auth 필요 | ❌ 앱 수정 불필요 |
| 2026-03-18 | legacy auth 제거 (`/auth/register`, `/auth/login`, `/auth/refresh`) | 현재 앱은 해당 경로를 사용하지 않음 | ❌ 앱 수정 불필요 |
| 2026-03-18 | board/blog 읽기 경로를 `X-API-Key + 인증` 필수로 강화 | 앱은 기존 인증 헤더 흐름을 유지하며 외부 비로그인 조회만 차단됨 | ❌ 앱 수정 불필요 |
| 2026-03-18 | PDF API를 `X-API-Key + 인증` 필수로 강화 | 앱 PDF 기능은 기존 인터셉터/토큰 흐름으로 유지 | ❌ 앱 수정 불필요 |
| 2026-03-18 | `POST /api/v1/auth/logout`에 `X-CSRF-Token` 필수화 | 앱 logout이 `/auth/me`에서 받은 `csrf_token`을 함께 전송하도록 동시 반영 | ✅ 앱 동시 반영 |
| 2026-03-18 | chat message `sender_name`, board comment `author.nickname` 응답 계약 보강 | 앱 채팅/댓글에서 내부 ID 대신 닉네임/이름을 표시하도록 동시 반영 | ✅ 앱 동시 반영 |
| 2026-03-18 | 블로그 작성자 모델에 `nickname` 매핑 추가 | 블로그 목록/상세에서 작성자 닉네임 우선 표시 | ✅ 앱 동시 반영 |

---

## 갱신 규칙

- API 엔드포인트 추가/변경/삭제 시 이 매트릭스 반드시 갱신
- 유저 스토리 변경 시 연관 테스트 케이스도 함께 검토
- 관련 문서: [D/30_api_contract.md](../D/30_api_contract.md), [V/20_test_cases.md](../V/20_test_cases.md)

---

## COIN SIMULATOR 도메인

| 유저 스토리 | API 엔드포인트 | 테스트 케이스 | 상태 |
|------------|--------------|-------------|------|
| US-CS01: 시뮬레이터 대시보드 조회 | `GET /api/v1/coin-simulator/dashboard` | TC-CS01-01 | ✅ 완료 |
| US-CS02: superuser 시뮬레이터 제어 | `POST /api/v1/coin-simulator/start` | TC-CS02-01 | ✅ 완료 |
| US-CS02: superuser 설정 저장 | `PUT /api/v1/coin-simulator/settings` | TC-CS02-02 | ✅ 완료 |

---

## LEDGER 도메인

| 유저 스토리 | API 엔드포인트 | 테스트 케이스 | 상태 |
|------------|--------------|-------------|------|
| US-L01: 관리자 일일 원장 생성 | `POST /api/v1/verify/generate-daily/{date}` | TC-L01-01 ~ TC-L01-02 | ✅ 완료 |
