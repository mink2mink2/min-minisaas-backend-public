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
