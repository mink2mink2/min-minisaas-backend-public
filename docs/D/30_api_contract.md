# D/30 — API 계약 (API Contract)

> API가 변경될 때마다 이 문서를 먼저 갱신하고 코드를 수정한다.
> 앱(Flutter) 연동에 영향을 주는 변경은 `R/40_traceability.md`도 함께 갱신한다.

**Base URL**: `https://api.yourdomain.com`
**API Version**: `v1`
**인증**: `Authorization: Bearer {jwt_token}` (별도 표기 없으면 필수)

---

## 공통 응답 형식

### 성공 응답
```json
// 단일 객체
{ "id": 1, "field": "value", ... }

// 목록
{ "items": [...], "total": 100, "skip": 0, "limit": 20 }
```

### 에러 응답
```json
{ "detail": "에러 메시지" }
// 또는 유효성 검사 오류
{ "detail": [{"loc": ["body", "field"], "msg": "field required", "type": "value_error"}] }
```

### 공통 HTTP 상태 코드

| 코드 | 의미 |
|------|------|
| 200 | 성공 (조회, 수정) |
| 201 | 생성 성공 |
| 204 | 삭제 성공 (응답 본문 없음) |
| 400 | 잘못된 요청 |
| 401 | 인증 실패 (토큰 없음/만료/위조) |
| 403 | 권한 없음 |
| 404 | 리소스 없음 |
| 409 | 충돌 (중복) |
| 422 | 유효성 검사 실패 |
| 429 | Rate Limit 초과 |
| 503 | 외부 서비스 오류 |

---

## AUTH 도메인 `/api/v1/auth`

### POST /api/v1/auth/login/google
Google Firebase ID Token으로 로그인하고 JWT를 발급받는다.

**인증**: 불필요

**Request Body**:
```json
{
  "id_token": "eyJhbGci..."  // Firebase ID Token
}
```

**Response 200**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "nickname": "홍길동",
    "provider": "google",
    "profile_image": "https://...",
    "created_at": "2026-02-01T00:00:00Z"
  }
}
```

**에러**:
- `401` — 유효하지 않거나 만료된 Firebase ID Token

---

### POST /api/v1/auth/login/kakao
Kakao Access Token으로 로그인한다. 서버에서 카카오 API를 통해 검증한다.

**인증**: 불필요

**Request Body**:
```json
{
  "access_token": "kakao_access_token_here"
}
```

**Response 200**: (Google 로그인과 동일 구조, `"provider": "kakao"`)

**에러**:
- `401` — 유효하지 않은 카카오 토큰
- `503` — 카카오 API 서버 오류

---

### POST /api/v1/auth/login/naver
Naver Access Token으로 로그인한다. 서버에서 네이버 API를 통해 검증한다.

**인증**: 불필요

**Request Body**:
```json
{
  "access_token": "naver_access_token_here"
}
```

**Response 200**: (Google 로그인과 동일 구조, `"provider": "naver"`)

---

### POST /api/v1/auth/logout
현재 기기에서 로그아웃한다. FCM 토큰을 비활성화한다.

**Request Body**:
```json
{
  "fcm_token": "fcm_token_to_deactivate"  // 선택
}
```

**Response 200**:
```json
{ "message": "Successfully logged out" }
```

---

### GET /api/v1/auth/me
현재 로그인된 사용자 정보를 반환한다.

**Response 200**:
```json
{
  "id": 1,
  "email": "user@gmail.com",
  "nickname": "홍길동",
  "provider": "google",
  "profile_image": "https://...",
  "is_admin": false,
  "created_at": "2026-02-01T00:00:00Z"
}
```

---

## CHAT 도메인 `/api/v1/chat`

### GET /api/v1/chat/rooms
내가 참여 중인 채팅방 목록을 최신 메시지 순으로 반환한다.

**Response 200**:
```json
{
  "items": [
    {
      "id": 1,
      "type": "direct",
      "participants": [
        { "id": 2, "nickname": "김철수", "profile_image": "https://..." }
      ],
      "last_message": {
        "content": "안녕하세요",
        "sender_id": 2,
        "created_at": "2026-03-01T12:00:00Z"
      },
      "unread_count": 3,
      "created_at": "2026-02-15T10:00:00Z"
    }
  ]
}
```

---

### POST /api/v1/chat/rooms
1:1 채팅방을 생성한다. 이미 존재하면 기존 채팅방을 반환한다.

**Request Body**:
```json
{
  "target_user_id": 2  // 상대방 사용자 ID
}
```

**Response 201** (신규) / **200** (기존):
```json
{
  "id": 1,
  "type": "direct",
  "participants": [...],
  "created_at": "2026-02-15T10:00:00Z"
}
```

**에러**:
- `400` — 자기 자신과 채팅방 생성 시도
- `404` — target_user_id 사용자 없음

---

### GET /api/v1/chat/rooms/{room_id}/messages
채팅방의 메시지 이력을 페이지네이션으로 반환한다.

**Path Params**: `room_id` (integer)
**Query Params**: `skip=0`, `limit=50`

**Response 200**:
```json
{
  "items": [
    {
      "id": 100,
      "room_id": 1,
      "sender_id": 1,
      "sender_nickname": "홍길동",
      "content": "안녕하세요",
      "message_type": "text",
      "created_at": "2026-03-01T12:00:00Z"
    }
  ],
  "total": 250,
  "skip": 0,
  "limit": 50
}
```

**에러**: `403` — 채팅방 참여자가 아님

---

### POST /api/v1/chat/rooms/{room_id}/messages
HTTP를 통해 메시지를 전송한다 (WebSocket 폴백).

**Request Body**:
```json
{
  "content": "안녕하세요",
  "message_type": "text"
}
```

**Response 201**:
```json
{
  "id": 101,
  "room_id": 1,
  "sender_id": 1,
  "content": "안녕하세요",
  "created_at": "2026-03-01T12:01:00Z"
}
```

---

## COIN SIMULATOR 도메인 `/api/v1/coin-simulator`

### GET /api/v1/coin-simulator/dashboard
시뮬레이터 상태/자산/포지션/최근 거래를 조회한다.
Cloud Run API는 Redis 캐시를 우선 사용하고, 캐시 미스 시 로컬 코인 서버 API에서 최신 스냅샷을 가져온다.

### POST /api/v1/coin-simulator/start
superuser만 시뮬레이터를 시작할 수 있다.
Cloud Run API가 로컬 코인 서버의 `/api/bot/start`를 호출한 뒤 캐시를 갱신한다.

### POST /api/v1/coin-simulator/stop
superuser만 시뮬레이터를 중지할 수 있다.
Cloud Run API가 로컬 코인 서버의 `/api/bot/stop`을 호출한 뒤 캐시를 갱신한다.

### PUT /api/v1/coin-simulator/settings
superuser만 시뮬레이터 설정을 변경할 수 있다.
Cloud Run API가 로컬 코인 서버의 전략 설정 API를 호출한 뒤 캐시를 갱신한다.

**Request Body**:
```json
{
  "mode": "paper",
  "exchange": "binance",
  "refresh_interval_seconds": 5,
  "analysis_limit": 30,
  "default_order_amount": 100.0,
  "risk_per_trade_pct": 1.0,
  "auto_stop_loss_pct": 2.0,
  "auto_take_profit_pct": 3.0,
  "enabled_strategies": ["bb_strategy"]
}
```

---

### WS /api/v1/chat/ws/rooms/{room_id}
실시간 채팅 WebSocket 연결.

**연결 URL**: `wss://api.yourdomain.com/api/v1/chat/ws/rooms/{room_id}?token={jwt_token}`

**수신 메시지 형식**:
```json
{
  "type": "message",
  "data": {
    "id": 101,
    "sender_id": 2,
    "sender_nickname": "김철수",
    "content": "안녕하세요",
    "created_at": "2026-03-01T12:01:00Z"
  }
}
```

**전송 메시지 형식**:
```json
{
  "content": "반갑습니다",
  "message_type": "text"
}
```

**연결 거부**: 토큰 없음/만료 시 WebSocket 코드 `4001`로 연결 거부

---

## BOARD 도메인 `/api/v1/board`

### GET /api/v1/board/posts
게시글 목록 조회.

**인증**: 불필요 (인증 시 내 반응 정보 포함)
**Query Params**: `skip=0`, `limit=20`, `category=string`, `search=string`, `sort=latest|popular`

**Response 200**:
```json
{
  "items": [
    {
      "id": 1,
      "title": "첫 번째 게시글",
      "content": "내용 미리보기...",
      "author": { "id": 1, "nickname": "홍길동" },
      "category": "자유",
      "tags": ["개발", "FastAPI"],
      "likes_count": 10,
      "comments_count": 5,
      "view_count": 100,
      "my_reaction": { "liked": true, "bookmarked": false },
      "created_at": "2026-02-20T09:00:00Z"
    }
  ],
  "total": 150,
  "skip": 0,
  "limit": 20
}
```

---

### POST /api/v1/board/posts
게시글 작성.

**Request Body**:
```json
{
  "title": "제목 (최대 255자)",
  "content": "내용",
  "category": "자유",
  "tags": ["개발", "FastAPI"]
}
```

**Response 201**: 생성된 게시글 (위 목록 아이템과 동일 구조)

**Rate Limit**: 10개/분

---

### GET /api/v1/board/posts/{id}
게시글 상세 조회.

**Response 200**: 목록 아이템과 동일 구조 (전체 내용 포함)

**에러**: `404` — 존재하지 않거나 삭제된 게시글

---

### PUT /api/v1/board/posts/{id}
게시글 수정 (본인만).

**Request Body**:
```json
{
  "title": "수정된 제목",
  "content": "수정된 내용",
  "category": "개발",
  "tags": ["Python"]
}
```

**Response 200**: 수정된 게시글
**에러**: `403` — 본인 게시글이 아님

---

### DELETE /api/v1/board/posts/{id}
게시글 삭제 (본인 또는 관리자). 소프트 삭제.

**Response 204** (본문 없음)

---

### POST /api/v1/board/posts/{id}/like
게시글 좋아요.

**Response 201**:
```json
{ "likes_count": 11 }
```

**에러**: `409` — 이미 좋아요 함

---

### DELETE /api/v1/board/posts/{id}/like
게시글 좋아요 취소.

**Response 200**:
```json
{ "likes_count": 10 }
```

---

### POST /api/v1/board/posts/{id}/bookmark
게시글 북마크.

**Response 201**: `{ "message": "Bookmarked" }`
**에러**: `409` — 이미 북마크 함

---

### DELETE /api/v1/board/posts/{id}/bookmark
북마크 취소.

**Response 204**

---

### GET /api/v1/board/posts/{id}/comments
댓글 목록 조회.

**Query Params**: `skip=0`, `limit=50`

**Response 200**:
```json
{
  "items": [
    {
      "id": 1,
      "content": "좋은 글이네요",
      "author": { "id": 2, "nickname": "김철수" },
      "parent_id": null,
      "created_at": "2026-02-20T10:00:00Z"
    }
  ]
}
```

---

### POST /api/v1/board/posts/{id}/comments
댓글 작성.

**Request Body**:
```json
{
  "content": "댓글 내용",
  "parent_id": null  // 대댓글이면 부모 댓글 ID
}
```

**Response 201**: 생성된 댓글
**Rate Limit**: 1개/초

---

### DELETE /api/v1/board/comments/{id}
댓글 삭제 (본인 또는 관리자). 소프트 삭제.

**Response 204**

---

## BLOG 도메인 `/api/v1/blogs`

### GET /api/v1/blogs/feed
내가 구독한 블로거들의 최신 글 피드.

**Query Params**: `skip=0`, `limit=20`

**Response 200**:
```json
{
  "items": [
    {
      "id": 1,
      "title": "FastAPI 심층 분석",
      "content": "미리보기...",
      "slug": "fastapi-deep-dive",
      "author": { "id": 3, "nickname": "이개발" },
      "category": "개발",
      "likes_count": 25,
      "view_count": 500,
      "my_liked": false,
      "created_at": "2026-03-01T08:00:00Z"
    }
  ]
}
```

---

### GET /api/v1/blogs
블로그 게시글 전체 목록.

**인증**: 불필요
**Query Params**: `skip=0`, `limit=20`, `category=string`, `author_id=integer`, `sort=latest|popular`

**Response 200**: 피드와 동일 구조

---

### POST /api/v1/blogs
블로그 게시글 작성.

**Request Body**:
```json
{
  "title": "제목",
  "content": "마크다운 내용",
  "category": "개발",
  "tags": ["Python", "FastAPI"],
  "is_published": true
}
```

**Response 201**: 생성된 블로그 포스트

---

### GET /api/v1/blogs/{id}
블로그 게시글 상세 (조회수 증가).

**Response 200**: 전체 내용 포함한 블로그 포스트

---

### PUT /api/v1/blogs/{id}
블로그 수정 (본인만).

**Request Body**: POST와 동일
**Response 200**: 수정된 게시글

---

### DELETE /api/v1/blogs/{id}
블로그 삭제 (본인만).

**Response 204**

---

### POST /api/v1/blogs/{id}/like
블로그 좋아요.

**Response 201**: `{ "likes_count": 26 }`
**에러**: `409`

---

### DELETE /api/v1/blogs/{id}/like
블로그 좋아요 취소.

**Response 200**: `{ "likes_count": 25 }`

---

### POST /api/v1/blogs/{id}/subscribe
블로거 구독. `{id}`는 블로그 포스트 ID가 아닌 **작성자(user) ID**.

**Response 201**: `{ "message": "Subscribed" }`
**에러**: `409` — 이미 구독, `400` — 자기 자신 구독

---

### DELETE /api/v1/blogs/{id}/subscribe
구독 취소.

**Response 204**

---

## PUSH 도메인 `/api/v1/push`

### POST /api/v1/push/tokens
FCM 토큰 등록. 이미 존재하면 갱신.

**Request Body**:
```json
{
  "token": "fcm_registration_token",
  "platform": "android"  // "ios" 또는 "android"
}
```

**Response 201** (신규) / **200** (기존 갱신):
```json
{
  "id": 1,
  "token": "fcm_registration_token",
  "platform": "android",
  "active": true,
  "created_at": "2026-03-01T00:00:00Z"
}
```

---

### PUT /api/v1/push/tokens/{id}
FCM 토큰 갱신.

**Request Body**:
```json
{
  "token": "new_fcm_token"
}
```

**Response 200**: 갱신된 토큰 레코드

---

### DELETE /api/v1/push/tokens/{token}
FCM 토큰 삭제 (로그아웃 시).

**Response 204**

---

### GET /api/v1/push/notifications
내 알림 목록.

**Query Params**: `skip=0`, `limit=20`, `unread_only=false`

**Response 200**:
```json
{
  "items": [
    {
      "id": 1,
      "title": "새 댓글",
      "body": "홍길동님이 댓글을 남겼습니다.",
      "type": "board",
      "read": false,
      "data": {
        "route": "/board/posts/1",
        "post_id": 1
      },
      "created_at": "2026-03-01T12:00:00Z"
    }
  ],
  "total": 15
}
```

---

### GET /api/v1/push/notifications/unread/count
읽지 않은 알림 수.

**Response 200**:
```json
{ "count": 5 }
```

---

### PUT /api/v1/push/notifications/{id}/read
특정 알림 읽음 처리.

**Response 200**:
```json
{ "id": 1, "read": true }
```

**에러**: `403` — 내 알림이 아님

---

### PUT /api/v1/push/notifications/read-all
모든 알림 읽음 처리.

**Response 200**:
```json
{ "updated_count": 5 }
```

---

### DELETE /api/v1/push/notifications/{id}
알림 삭제.

**Response 204**
**에러**: `403` — 내 알림이 아님

---

## 헬스체크

### GET /health
서비스 상태 확인.

**인증**: 불필요

**Response 200**:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2026-03-03T00:00:00Z"
}
```

**Response 503**: DB 또는 Redis 연결 실패 시

---

## API 변경 이력

| 날짜 | 변경 내용 | 영향 |
|------|----------|------|
| 2026-02-11 | Auth, Chat API 최초 구현 | - |
| 2026-02-15 | Board API 추가 | Flutter Board 화면 |
| 2026-02-20 | Blog API 추가 | Flutter Blog 화면 |
| 2026-02-25 | Push API 추가 | Flutter 알림 화면 |
| 2026-03-01 | unread/count 엔드포인트 추가 | 앱 탭바 뱃지 |

---

# Flutter PDF 코드 가이드

## 📂 파일 위치

생성된 Flutter 파일들이 `flutter-pdf-code/` 디렉토리에 있습니다:

```
flutter-pdf-code/
├── pdf_models.dart        (3.0 KB)
├── pdf_service.dart       (5.5 KB)
└── pdf_providers.dart     (8.1 KB)
```

## 🚀 통합 방법

### 1단계: Flutter 프로젝트에 복사

```bash
# 이 명령을 Flutter 프로젝트 루트에서 실행
cp <backend-path>/flutter-pdf-code/*.dart lib/domain/ai/

# 또는 각각 복사
cp <backend-path>/flutter-pdf-code/pdf_models.dart lib/domain/ai/models/
cp <backend-path>/flutter-pdf-code/pdf_service.dart lib/domain/ai/services/
cp <backend-path>/flutter-pdf-code/pdf_providers.dart lib/domain/ai/providers/
```

### 2단계: 필수 의존성 설치

```bash
flutter pub add dio flutter_riverpod path_provider
```

**pubspec.yaml:**
```yaml
dependencies:
  dio: ^5.0.0
  flutter_riverpod: ^2.0.0
  path_provider: ^2.0.0
```

### 3단계: API Client Provider 설정

`lib/core/providers/api_providers.dart` 또는 `lib/domain/ai/providers/` 에 다음을 추가:

```dart
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final apiClientProvider = Provider<Dio>((ref) {
  final dio = Dio(BaseOptions(
    baseUrl: 'https://your-api-domain.com',  // 본인 API 주소로 변경
    connectTimeout: const Duration(seconds: 30),
    receiveTimeout: const Duration(seconds: 30),
  ));

  // 인증 토큰 헤더 추가
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) {
        // 토큰 추가 로직
        // options.headers['Authorization'] = 'Bearer $token';
        return handler.next(options);
      },
    ),
  );

  return dio;
});
```

## 📱 사용 예시

### 파일 업로드

```dart
import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'domain/ai/providers/pdf_providers.dart';

class UploadPdfPage extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ElevatedButton(
      onPressed: () async {
        final pdfFile = File('/path/to/file.pdf');
        try {
          final uploaded = await ref
              .read(pdfFilesProvider.notifier)
              .uploadFile(pdfFile);
          
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('업로드 완료: ${uploaded.fileId}')),
          );
        } catch (e) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('업로드 실패: $e')),
          );
        }
      },
      child: const Text('PDF 업로드'),
    );
  }
}
```

### 파일 목록 조회

```dart
class PdfListPage extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filesAsync = ref.watch(pdfFilesProvider);

    return filesAsync.when(
      data: (files) => ListView.builder(
        itemCount: files.length,
        itemBuilder: (context, index) {
          final file = files[index];
          return ListTile(
            title: Text(file.originalFilename),
            subtitle: Text('Status: ${file.status}'),
            trailing: file.status == 'processed'
                ? IconButton(
                    icon: const Icon(Icons.download),
                    onPressed: () => _downloadFile(context, ref, file.fileId),
                  )
                : const CircularProgressIndicator(),
          );
        },
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, stack) => Center(child: Text('Error: $err')),
    );
  }

  Future<void> _downloadFile(
    BuildContext context,
    WidgetRef ref,
    String fileId,
  ) async {
    try {
      final dir = await getApplicationDocumentsDirectory();
      final savePath = '${dir.path}/$fileId.csv';

      await ref.read(pdfServiceProvider).downloadCsv(fileId, savePath);
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('다운로드 완료: $savePath')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('다운로드 실패: $e')),
      );
    }
  }
}
```

### 변환 요청 및 폴링

```dart
class ConvertPdfPage extends ConsumerWidget {
  final String fileId;

  const ConvertPdfPage({required this.fileId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ElevatedButton(
      onPressed: () async {
        try {
          // 변환 요청
          final notifier = ref.read(pdfConversionStatusProvider(fileId).notifier);
          await notifier.requestConversion();
          
          // 자동 폴링 시작 (최대 10분)
          await notifier.pollStatus();
          
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('변환 완료!')),
          );
        } on InsufficientPointsException catch (e) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('포인트 부족: $e')),
          );
        } catch (e) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('변환 실패: $e')),
          );
        }
      },
      child: const Text('PDF 변환 시작'),
    );
  }
}
```

### 변환 진행 상태 모니터링

```dart
class ConversionProgressPage extends ConsumerWidget {
  final String fileId;

  const ConversionProgressPage({required this.fileId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final progressAsync = ref.watch(conversionProgressProvider(fileId));

    return progressAsync.when(
      data: (progress) {
        final statusMap = {
          'uploading': '파일 업로드 중...',
          'requesting': '변환 요청 중...',
          'processing': '변환 처리 중...',
          'processed': '변환 완료!',
        };

        return Column(
          children: [
            LinearProgressIndicator(
              value: ['uploading', 'requesting', 'processing', 'processed']
                  .indexOf(progress) /
                  4,
            ),
            SizedBox(height: 16),
            Text(statusMap[progress] ?? progress),
          ],
        );
      },
      loading: () => const CircularProgressIndicator(),
      error: (err, stack) => Text('Error: $err'),
    );
  }
}
```

### 다운로드 진행률 표시

```dart
Future<void> downloadWithProgress(
  BuildContext context,
  WidgetRef ref,
  String fileId,
) async {
  final pdfService = ref.read(pdfServiceProvider);
  final dir = await getApplicationDocumentsDirectory();
  final savePath = '${dir.path}/$fileId.csv';

  await pdfService.downloadCsvWithProgress(
    fileId,
    savePath,
    onProgress: (received, total) {
      final progress = total > 0 ? received / total : 0;
      print('Download progress: ${(progress * 100).toStringAsFixed(1)}%');
    },
  );
}
```

## 🔄 전체 플로우 예시

```dart
// 1. 파일 선택 및 업로드
File pdfFile = ...;
final uploadedFile = await pdfService.uploadPdf(pdfFile);

// 2. 변환 요청
try {
  final status = await pdfService.requestConversion(uploadedFile.fileId);
  print('변환 시작: ${status.status}');
} on InsufficientPointsException {
  print('포인트 부족!');
  return;
}

// 3. 상태 폴링 (수동)
while (true) {
  final status = await pdfService.getStatus(uploadedFile.fileId);
  
  if (status.status == 'processed') {
    print('변환 완료!');
    break;
  } else if (status.status == 'failed') {
    print('변환 실패!');
    break;
  }
  
  await Future.delayed(Duration(seconds: 2));
}

// 4. CSV 다운로드
final dir = await getApplicationDocumentsDirectory();
final savePath = '${dir.path}/output.csv';
await pdfService.downloadCsv(uploadedFile.fileId, savePath);

// 5. 파일 삭제 (선택)
await pdfService.deleteFile(uploadedFile.fileId);
```

## ⚙️ 커스터마이징

### API 기본 URL 변경

```dart
// pubspec.yaml 또는 config 파일에서 관리
final apiClientProvider = Provider<Dio>((ref) {
  final apiUrl = const String.fromEnvironment(
    'API_URL',
    defaultValue: 'https://api.example.com',
  );
  
  return Dio(BaseOptions(baseUrl: apiUrl));
});
```

### 폴링 간격 수정

```dart
await notifier.pollStatus(
  interval: const Duration(seconds: 5),  // 5초마다 확인
  timeout: const Duration(minutes: 30),  // 최대 30분
);
```

### 예외 처리

```dart
try {
  await pdfService.requestConversion(fileId);
} on InsufficientPointsException catch (e) {
  // 포인트 부족 처리
  print(e.message);
} on PdfServiceException catch (e) {
  // 일반 서비스 에러
  print('HTTP ${e.statusCode}: ${e.message}');
} catch (e) {
  // 기타 에러
  print('Unknown error: $e');
}
```

## 🧪 테스트 팁

```dart
// Mock 서비스 생성
class MockPdfService extends Mock implements PdfService {}

// Provider override
testWidgets('Upload test', (WidgetTester tester) async {
  final mockService = MockPdfService();
  
  await tester.pumpWidget(
    ProviderContainer(
      overrides: [
        pdfServiceProvider.overrideWithValue(mockService),
      ],
      child: const MyApp(),
    ),
  );
});
```

## 📚 클래스 참조

### PdfFile
```dart
class PdfFile {
  final String fileId;
  final String originalFilename;
  final int fileSizeBytes;
  final String status;
  final int? pageCount;
  final int conversionCost;
  final String? outputPath;
  final DateTime createdAt;
  final DateTime? processedAt;
}
```

### PdfConversionStatus
```dart
class PdfConversionStatus {
  final String fileId;
  final String status;
  final int conversionCost;
  final String? outputPath;
  final String message;
  final DateTime createdAt;
  final DateTime? processedAt;
}
```

## 🎯 주의사항

1. **API URL**: `apiClientProvider`에서 올바른 API 주소 설정
2. **인증**: Authorization 헤더 추가 필수
3. **권한**: 파일 읽기/쓰기 권한 확인 (path_provider 사용)
4. **네트워크**: 장시간 변환 시 연결 타임아웃 관리
5. **스토리지**: 다운로드 파일 크기 및 저장 공간 확인

## 🐛 문제 해결

### "apiClientProvider not found"
→ `pdf_providers.dart`에서 apiClientProvider 정의 또는 임포트 필요

### "Connection timeout"
→ Dio BaseOptions에서 connectTimeout/receiveTimeout 값 증가

### "Permission denied" (파일 저장)
→ AndroidManifest.xml / Info.plist 권한 설정 확인

### "HTTP 402"
→ 사용자 포인트 부족, 포인트 충전 후 재시도
